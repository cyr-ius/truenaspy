"""TrueNAS API."""

from __future__ import annotations

from datetime import datetime, timedelta
from logging import getLogger
from typing import Any, Self

from aiohttp import ClientSession
import semantic_version

from .auth import Auth
from .collect import (
    Alert,
    App,
    Boot,
    Charts,
    CloudSync,
    Dataset,
    Disk,
    Docker,
    Interface,
    Jail,
    Job,
    Pool,
    Replication,
    Rsync,
    Service,
    Smart,
    Snapshottask,
    System,
    Update,
    VirtualMachine,
)
from .exceptions import NotFoundError, TruenasException
from .helper import (
    ExtendedDict,
    as_local,
    b2gib,
    systemstats_process,
    utc_from_timestamp,
)
from .subscription import Events, Subscriptions

_LOGGER = getLogger(__name__)


class TruenasClient(object):
    """Handle all communication with TrueNAS."""

    def __init__(
        self,
        host: str,
        token: str,
        session: ClientSession | None = None,
        use_ssl: bool = False,
        verify_ssl: bool = True,
        scan_intervall: int = 60,
        timeout: int = 300,
    ) -> None:
        """Initialize the TrueNAS API."""
        session = session or ClientSession()
        self.auth = Auth(session, host, token, use_ssl, verify_ssl, timeout)
        self.async_request = self.auth.async_request

        self._is_scale: bool = False
        self._is_virtual: bool = False
        self._sub = Subscriptions(
            (self.async_update, self.async_is_alive), scan_intervall
        )
        self.is_connected: bool = False
        self.is_alerts: bool = False
        self._systemstats_errored: list[str] = []
        self.alerts: list[dict[str, Any]] = []
        self.charts: list[dict[str, Any]] = []
        self.apps: list[dict[str, Any]] = []
        self.cloudsync: list[dict[str, Any]] = []
        self.datasets: list[dict[str, Any]] = []
        self.disks: list[dict[str, Any]] = []
        self.interfaces: list[dict[str, Any]] = []
        self.jails: list[dict[str, Any]] = []
        self.pools: list[dict[str, Any]] = []
        self.replications: list[dict[str, Any]] = []
        self.rsynctasks: list[dict[str, Any]] = []
        self.services: list[dict[str, Any]] = []
        self.smartdisks: list[dict[str, Any]] = []
        self.snapshots: list[dict[str, Any]] = []
        self.stats: dict[str, Any] = {}
        self.system_infos: dict[str, Any] = {}
        self.update_infos: dict[str, Any] = {}
        self.docker: dict[str, Any] = {}
        self.virtualmachines: list[dict[str, Any]] = []

    async def async_get_system(self) -> dict[str, Any]:
        """Get system info from TrueNAS."""
        response = await self.async_get_system_info()
        self.system_infos = System.from_dict(response).to_dict()

        response = await self.async_request("system/version_short")
        self.system_infos.update({"short_version": response})

        try:
            response = await self.async_request("system/is_freenas")
            check = bool(response)
        except TruenasException:
            rsp = str(await self.async_request("system/product_type"))
            check = "SCALE" not in rsp

        self._is_scale = check is False
        self._is_virtual = self.system_infos["system_manufacturer"] in [
            "QEMU",
            "VMware, Inc.",
        ] or self.system_infos["system_product"] in ["VirtualBox"]

        if (uptime := self.system_infos["uptime_seconds"]) > 0:
            now = datetime.now().replace(microsecond=0)
            uptime_tm = datetime.timestamp(now - timedelta(seconds=int(uptime)))
            self.system_infos.update(
                {
                    "uptimeEpoch": str(
                        as_local(utc_from_timestamp(uptime_tm)).isoformat()
                    )
                }
            )

        # Get stats.
        query = [
            {"name": "load"},
            {"name": "cpu"},
            {"name": "arcsize"},
            {"name": "arcrate"},
            {"name": "arcactualrate"},
            {"name": "arcresult"},
            {"name": "memory"},
            # {"name": "swap"},
        ]

        if not self._is_virtual:
            query.append({"name": "cputemp"})

        stats: list[dict[str, Any]] = await self.async_get_stats(query)
        for item in stats:
            # CPU temperature
            if item.get("name") == "cputemp" and "aggregations" in item:
                self.system_infos["cpu_temperature"] = round(
                    max(item["aggregations"]["mean"].values()), 1
                )

            # CPU load
            if item.get("name") == "load":
                tmp_arr = ["shortterm", "midterm", "longterm"]
                systemstats_process(self.system_infos, tmp_arr, item, "load")

            # CPU usage
            if item.get("name") == "cpu":
                tmp_arr = ["interrupt", "system", "user", "nice", "idle"]
                systemstats_process(self.system_infos, tmp_arr, item, "cpu")
                self.system_infos["cpu_usage"] = round(
                    self.system_infos["cpu_system"] + self.system_infos["cpu_user"], 2
                )

            # memory
            if item.get("name") == "memory":
                tmp_arr = ["used", "free", "cached", "buffers"]
                systemstats_process(self.system_infos, tmp_arr, item, "memory")
                self.system_infos["memory_total_value"] = round(
                    self.system_infos["memory_used"]
                    + self.system_infos["memory_free"]
                    + self.system_infos["memory_arc_size"],
                    2,
                )
                if (total_value := self.system_infos["memory_total_value"]) > 0:
                    self.system_infos["memory_usage_percent"] = round(
                        100
                        * (float(total_value) - float(self.system_infos["memory_free"]))
                        / float(total_value),
                        0,
                    )

                self.system_infos["arc_size_ratio"] = round(
                    self.system_infos["memory_arc_size"]
                    * 100
                    / self.system_infos["memory_total_value"],
                    2,
                )

            # Swap
            if item.get("name") == "swap":
                tmp_arr = ["free", "used"]
                systemstats_process(self.system_infos, tmp_arr, item, "swap")

            # arcsize
            if item.get("name") == "arcsize":
                tmp_arr = ["arc_size"]
                systemstats_process(self.system_infos, tmp_arr, item, "memory")

            # arcactualrate ZFS Actual Cache Hits Rate
            if item.get("name") == "arcactualrate":
                tmp_arr = ["hits", "misses"]
                systemstats_process(self.system_infos, tmp_arr, item, "arc")

            # arcrate ZFS ARC Hits Rate
            if item.get("name") == "arcrate":
                tmp_arr = ["hits", "misses"]
                systemstats_process(self.system_infos, tmp_arr, item, "arc")

            # arcrate ZZFS ARC Result
            if item.get("name") == "arcresult":
                tmp_arr = []
                systemstats_process(self.system_infos, tmp_arr, item, "arc")

        self._sub.notify(Events.SYSTEM.value)
        return self.system_infos

    async def async_restart_system(self) -> None:
        """Restart system."""
        await self.async_request("system/reboot", method="post")

    async def async_shutdown_system(self) -> None:
        """Restart system."""
        await self.async_request("system/shutdown", method="post")

    async def async_update_system(self, reboot: bool = False) -> None:
        """Update system."""
        await self.async_request(
            "update/update", method="post", json={"reboot": reboot}
        )

    async def async_get_system_info(self) -> Any:
        """Get system info from TrueNAS."""
        return await self.async_request("system/info")

    async def async_get_interfaces(self) -> list[dict[str, Any]]:
        """Get interface info from TrueNAS."""
        response = await self.async_request("interface")
        self.interfaces = [Interface.from_dict(item).to_dict() for item in response]

        # Get stats
        query = [
            {"name": "interface", "identifier": interface["id"]}
            for interface in self.interfaces
        ]
        stats = await self.async_get_stats(query)
        for interface in self.interfaces:
            for item in stats:
                # Interface
                if (
                    item.get("name") == "interface"
                    and item["identifier"] == interface["id"]
                ):
                    # 12->13 API change
                    item["legend"] = [
                        legend.replace("if_octets_", "") for legend in item["legend"]
                    ]
                    systemstats_process(interface, ["received", "sent"], item, "rx-tx")

        self._sub.notify(Events.INTERFACES.value)
        return self.interfaces

    async def async_get_stats(
        self, items: list[dict[str, Any]], aggregate: bool = True
    ) -> Any:
        """Get statistics."""
        now = datetime.now()
        start = int((now - timedelta(seconds=90)).timestamp())
        end = int((now - timedelta(seconds=30)).timestamp())
        query: dict[str, Any] = {
            "graphs": items,
            "reporting_query": {"start": start, "end": end, "aggregate": aggregate},
        }

        for param in query["graphs"]:
            if param["name"] in self._systemstats_errored:
                query["graphs"].remove(param)

        stats = []
        try:
            stats = await self.auth.async_request(
                "reporting/get_data", "post", json=query
            )

            if "error" in stats:
                for param in query["graphs"]:
                    await self.auth.async_request(
                        "reporting/get_data",
                        "post",
                        json={
                            "graphs": [param],
                            "reporting_query": {
                                "start": start,
                                "end": end,
                                "aggregate": True,
                            },
                        },
                    )
                    if "error" in stats:
                        self._systemstats_errored.append(param["name"])

                _LOGGER.warning(
                    "Fetching following graphs failed, check your NAS: %s",
                    self._systemstats_errored,
                )
                await self.async_get_stats(items)
        except TruenasException as error:
            # ERROR FIX: Cobia NAS-123862
            if self.system_infos.get("short_version") not in [
                "23.10.0",
                "23.10.0.0",
                "23.10.0.1",
            ]:
                _LOGGER.error(error)

        return stats

    async def async_get_services(self) -> list[dict[str, Any]]:
        """Get service info from TrueNAS."""
        response = await self.async_request("service")
        self.services = [Service.from_dict(item).to_dict() for item in response]
        self._sub.notify(Events.SERVICES.value)
        return self.services

    async def async_get_service(self, id: int) -> Any:
        """Get Service from TrueNAS."""
        return await self.async_request(f"service/id/{id}")

    async def async_reload_service(self, service: str) -> None:
        """Reload service."""
        await self.async_request(
            "service/reload", method="post", json={"service": service}
        )

    async def async_restart_service(self, service: str) -> None:
        """Restart service."""
        await self.async_request(
            "service/restart", method="post", json={"service": service}
        )

    async def async_stop_service(self, service: str) -> None:
        """Stop service."""
        await self.async_request(
            "service/stop", method="post", json={"service": service}
        )

    async def async_start_service(self, service: str) -> None:
        """Start service."""
        await self.async_request(
            "service/start", method="post", json={"service": service}
        )

    async def async_get_pools(self) -> list[dict[str, Any]]:
        """Get pools from TrueNAS."""
        response = await self.async_request("pool")
        self.pools = [Pool.from_dict(item).to_dict() for item in response]

        try:
            response = await self.async_request("boot/get_state")
        except TruenasException as error:
            _LOGGER.debug(error)
            response = ExtendedDict()

        boot = Boot.from_dict(response).to_dict()
        self.pools.append(boot)

        # Process pools
        dataset_available = {}
        dataset_total = {}
        for dataset in self.datasets:
            if mountpoint := dataset.get("mountpoint"):
                available = dataset.get("available", 0)
                used = dataset.get("used", 0)
                dataset_available[mountpoint] = b2gib(available)
                dataset_total[mountpoint] = b2gib(available + used)

        for pool in self.pools:
            if value := dataset_available.get(pool["path"]):
                pool.update({"available_gib": value})

            if value := dataset_total.get(pool["path"]):
                pool.update({"total_gib": value})

            if pool["name"] in ["boot-pool", "freenas-boot"]:
                if pool.get("root_dataset"):
                    available_gib = b2gib(pool["root_dataset"]["available"])
                    total_gib = b2gib(
                        pool["root_dataset"]["available"] + pool["root_dataset"]["used"]
                    )
                else:
                    available_gib = b2gib(pool["available"])
                    total_gib = b2gib(pool["size"])

                pool.update({"available_gib": available_gib, "total_gib": total_gib})

                # self.pools[uid].pop("root_dataset")

        self._sub.notify(Events.POOLS.value)
        return self.pools

    async def async_get_datasets(self) -> list[dict[str, Any]]:
        """Get datasets from TrueNAS."""
        # response = await self.async_request("pool/dataset/details")
        response = await self.async_request("pool/dataset")
        self.datasets = [Dataset.from_dict(item).to_dict() for item in response]
        self._sub.notify(Events.DATASETS.value)
        return self.datasets

    async def async_get_disks(self) -> list[dict[str, Any]]:
        """Get disks from TrueNAS."""
        response = await self.async_request("disk")
        self.disks = [Disk.from_dict(item).to_dict() for item in response]
        # Get disk temperatures
        temperatures = await self.auth.async_request(
            "disk/temperatures", "post", json={"names": []}
        )
        for disk in self.disks:
            disk.update({"temperature": temperatures.get(disk["name"], 0)})
        self._sub.notify(Events.DISKS.value)
        return self.disks

    async def async_get_jails(self) -> list[dict[str, Any]] | None:
        """Get jails from TrueNAS."""
        if self._is_scale is False:
            try:
                response = await self.async_request("jail")
                self.jails = [Jail.from_dict(item).to_dict() for item in response]
            except NotFoundError as error:
                _LOGGER.warning(error)
                self.jails = []
        self._sub.notify(Events.JAILS.value)
        return self.jails

    async def async_get_jail(self, id: int) -> Any:
        """Get jail."""
        return await self.async_request(f"jail/id/{id}")

    async def async_restart_jail(self, id: int) -> None:
        """Restart jail."""
        await self.async_request("jail/restart", method="post", json={"jail": id})

    async def async_stop_jail(self, id: int) -> None:
        """Stop jail."""
        await self.async_request("jail/stop", method="post", json={"jail": id})

    async def async_start_jail(self, id: int) -> None:
        """Start jail."""
        await self.async_request("jail/start", method="post", json={"jail": id})

    async def async_get_virtualmachines(self) -> list[dict[str, Any]]:
        """Get VMs from TrueNAS."""
        response = await self.async_request("vm")
        self.virtualmachines = [
            VirtualMachine.from_dict(item).to_dict() for item in response
        ]
        self._sub.notify(Events.VMS.value)
        return self.virtualmachines

    async def async_get_virtualmachine(self, id: int) -> Any:
        """Get virtualmachine."""
        return await self.async_request(f"vm/id/{id}")

    async def async_stop_virtualmachine(self, id: int) -> None:
        """Stop virtualmachine."""
        await self.async_request(f"vm/id/{id}/stop", method="post")

    async def async_start_virtualmachine(
        self, id: int, overcommit: bool = False
    ) -> None:
        """Start virtualmachine."""
        await self.async_request(
            f"vm/id/{id}/start", method="post", json={"overcommit": overcommit}
        )

    async def async_get_cloudsyncs(self) -> list[dict[str, Any]]:
        """Get cloudsync from TrueNAS."""
        response = await self.async_request("cloudsync")
        self.cloudsync = [CloudSync.from_dict(item).to_dict() for item in response]
        self._sub.notify(Events.CLOUD.value)
        return self.cloudsync

    async def async_get_cloudsync(self, id: int) -> Any:
        """Get cloudsync job."""
        return await self.async_request(f"cloudsync/id/{id}")

    async def async_sync_cloudsync(self, id: int) -> None:
        """Sync cloudsync job."""
        await self.async_request(f"cloudsync/id/{id}/sync", method="post")

    async def async_get_replications(self) -> list[dict[str, Any]]:
        """Get replication from TrueNAS."""
        response = await self.async_request("replication")
        self.replications = [Replication.from_dict(item).to_dict() for item in response]
        self._sub.notify(Events.REPLS.value)
        return self.replications

    async def async_get_snapshottasks(self) -> list[dict[str, Any]]:
        """Get replication from TrueNAS."""
        response = await self.async_request("pool/snapshottask")
        self.snapshots = [Snapshottask.from_dict(item).to_dict() for item in response]
        self._sub.notify(Events.SNAPS.value)
        return self.snapshots

    async def async_get_charts(self) -> list[dict[str, Any]]:
        """Get Charts from TrueNAS."""
        response = await self.async_request("chart/release")
        self.charts = [Charts.from_dict(item).to_dict() for item in response]
        self._sub.notify(Events.CHARTS.value)
        return self.charts

    async def async_get_chart(self, id: int) -> Any:
        """Get Charts from TrueNAS."""
        return await self.async_request(f"chart/release/id/{id}")

    async def async_update_chart(self, id: int) -> None:
        """Update chart."""
        await self.async_request(
            "chart/release/upgrade", method="post", json={"release_name": id}
        )

    async def async_update_chart_image(self, repo: str, tag: str) -> None:
        """Update chart image."""
        await self.async_request(
            "container/image/pull", method="post", json={"from_image": repo, "tag": tag}
        )

    async def async_stop_chart(self, id: int, replicas: int = 0) -> None:
        """Stop chart."""
        await self.async_request(
            "chart/release/scale",
            method="post",
            json={"release_name": id, "scale_options": {"replica_count": replicas}},
        )

    async def async_start_chart(self, id: int, replicas: int = 1) -> None:
        """Start chart."""
        await self.async_request(
            "chart/release/scale",
            method="post",
            json={"release_name": id, "scale_options": {"replica_count": replicas}},
        )

    async def async_get_docker(self) -> dict[str, Any]:
        """Get Charts from TrueNAS."""
        response = await self.async_request("docker/status")
        self.docker = Docker.from_dict(response).to_dict()
        # self._sub.notify(Events.CHARTS.value)
        return self.docker

    async def async_get_apps(self) -> list[dict[str, Any]]:
        """Get Charts from TrueNAS."""
        response = await self.async_request("app")
        self.apps = [App.from_dict(item).to_dict() for item in response]
        self._sub.notify(Events.APPS.value)
        return self.apps

    async def async_update_app(self, app_name: str) -> None:
        """Update chart image."""
        await self.async_request(
            "app/upgrade", method="post", json={"app_name": app_name}
        )

    async def async_pull_images(self, app_name: str) -> None:
        """Pull image chart image."""
        await self.async_request(
            "app/pull_images", method="post", json={"name": app_name}
        )

    async def async_outdated_images(self, app_name: str) -> None:
        """Returns a list of outdated docker images for the specified app."""
        await self.async_request(
            "app/outdated_docker_images", method="post", data=app_name
        )

    async def async_stop_app(self, app_name: str) -> None:
        """Stop chart."""
        await self.async_request("app/stop", method="post", json=app_name)

    async def async_start_app(self, app_name: str) -> None:
        """Stop chart."""
        await self.async_request("app/start", method="post", json=app_name)

    async def async_get_smartdisks(self) -> list[dict[str, Any]]:
        """Get smartdisk from TrueNAS."""
        response = await self.async_request("smart/test/results", params={"offset": 1})
        self.smartdisks = [Smart.from_dict(item).to_dict() for item in response]
        self._sub.notify(Events.SMARTS.value)
        return self.smartdisks

    async def async_get_alerts(self) -> list[dict[str, Any]]:
        """Get alerts from TrueNAS."""
        response = await self.async_request("alert/list")
        self.alerts = [Alert.from_dict(item).to_dict() for item in response]
        self.is_alerts = len(self.alerts) != 0
        self._sub.notify(Events.ALERTS.value)
        return self.alerts

    async def async_dismiss_alert(self, id: str) -> None:
        """Stop chart."""
        await self.async_request("alert/dismiss", method="post", json=id)

    async def async_get_rsynctasks(self) -> list[dict[str, Any]]:
        """Get smartdisk from TrueNAS."""
        response = await self.async_request("rsynctask")
        self.rsynctasks = [Rsync.from_dict(item).to_dict() for item in response]
        self._sub.notify(Events.RSYNC.value)
        return self.rsynctasks

    async def async_get_update_system(self) -> Any:
        """Check update available."""
        return await self.async_request("update/check_available", method="post")

    async def async_get_trains(self) -> Any:
        """Get trains update."""
        return await self.async_request("update/get_trains")

    async def async_get_jobs(self) -> Any:
        """Get core jobs."""
        return await self.async_request("core/get_jobs")

    async def async_get_job(self, id: int) -> Any:
        """Get core job."""
        return await self.async_request("core/get_jobs", params={"id": id})

    async def async_get_update(self) -> dict[str, Any]:
        """Get update info from TrueNAS."""
        try:
            response = await self.async_get_update_system()
        except TruenasException as error:
            _LOGGER.debug(error)
            response = ExtendedDict()
        self.update_infos = Update.from_dict(response).to_dict()

        try:
            response = await self.async_get_trains()
        except TruenasException as error:
            _LOGGER.debug(error)
            response = ExtendedDict()
        self.update_infos.update({"current_train": response.get("current")})

        if job_id := self.system_infos.get("job_id", 0):
            response = await self.async_get_job(job_id)
            jobs = [Job.from_dict(item).to_dict() for item in response]
            for job in jobs:
                if (
                    job.get("state") != "RUNNING"
                    or not self.update_infos["update_available"]
                ):
                    self.update_infos.update(
                        {"progress": 0, "status": None, "job_id": 0}
                    )
        return self.update_infos

    async def async_is_alive(self) -> bool:
        """Check connection."""
        result = await self.async_request("core/ping")
        return "pong" in result

    async def async_take_snapshot(self, name: str) -> None:
        """Create dataset snapshot."""
        ts = datetime.now().isoformat(sep="_", timespec="microseconds")
        await self.async_request(
            "zfs/snapshot",
            method="post",
            json={"dataset": name, "name": f"custom-{ts}"},
        )

    def subscribe(self, _callback: str, *args: Any) -> None:
        """Subscribe event."""
        self._sub.subscribe(_callback, *args)

    def unsubscribe(self, _callback: str, *args: Any) -> None:
        """Unsubscribe event."""
        self._sub.subscribe(_callback, *args)

    async def async_update(self) -> None:
        """Update all data."""

        version = await self.async_request("system/version")
        version_short = await self.async_request("system/version_short")
        is_scale = "SCALE" in version
        try:
            await self.async_is_alive()
            nb_events = len(Events)
            nb_errors = 0
            for event in Events:
                try:
                    if not is_scale and event.value == "charts":
                        continue
                    if is_scale and event.value == "jails":
                        continue
                    if (
                        is_scale
                        and event.value == "charts"
                        and semantic_version.Version.coerce(version_short)
                        >= semantic_version.Version.coerce("24.10.0.2")
                    ):
                        continue

                    fnc = getattr(self, f"async_get_{event.value}")
                    await fnc()
                except TruenasException as error:
                    _LOGGER.error(error)
                    nb_errors += 1
            self.is_connected = (
                False if nb_errors > 0 and nb_events == nb_errors else True
            )
        except TruenasException as error:
            _LOGGER.error(error)
            self.is_connected = False

    async def async_close(self) -> None:
        """Close open client session."""
        if self.auth._session:
            await self.auth._session.close()

    async def __aenter__(self) -> Self:
        """Async enter."""
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Async exit."""
        await self.async_close()
