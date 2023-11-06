"""TrueNAS API."""
from __future__ import annotations

from datetime import datetime, timedelta
from logging import getLogger
from typing import Any, Callable, Coroutine, Self

from aiohttp import ClientSession

from .auth import Auth
from .collects import (
    Alerts,
    Charts,
    CloudSync,
    Datasets,
    Disk,
    Interfaces,
    Jail,
    Job,
    Pool,
    Replication,
    Service,
    Smart,
    Snapshottask,
    System,
    Update,
    VirtualMachine,
)
from .exceptions import TruenasError
from .helper import (
    as_local,
    async_attributes,
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
        self._access = Auth(host, token, use_ssl, verify_ssl, timeout, session)
        self._is_scale: bool = False
        self._is_virtual: bool = False
        self._sub = Subscriptions(
            (self.async_update_all, self.async_is_alive), scan_intervall
        )
        self._systemstats_errored: list[str] = []
        self.query: Callable[
            [str, str, Any], Coroutine[Any, Any, Any]
        ] = self._access.async_request  # type: ignore[assignment]
        self.system: dict[str, Any] = {}
        self.interfaces: dict[str, Any] = {}
        self.stats: dict[str, Any] = {}
        self.services: dict[str, Any] = {}
        self.pools: dict[str, Any] = {}
        self.datasets: dict[str, Any] = {}
        self.disks: dict[str, Any] = {}
        self.jails: dict[str, Any] = {}
        self.virtualmachines: dict[str, Any] = {}
        self.cloudsync: dict[str, Any] = {}
        self.replications: dict[str, Any] = {}
        self.snapshots: dict[str, Any] = {}
        self.charts: dict[str, Any] = {}
        self.data: dict[str, Any] = {}
        self.smarts: dict[str, Any] = {}
        self.alerts: dict[str, Any] = {}

    async def async_get_system(self) -> dict[str, Any]:
        """Get system info from TrueNAS."""
        self.system = await async_attributes(System, self._access)

        # update_available
        update = await async_attributes(Update, self._access)

        update_available = update.get("update_status") == "AVAILABLE"
        self.system.update({"update_available": update_available})
        # update_version
        if not update_available:
            self.system.update({"update_version": self.system["version"]})

        if update_jobid := self.system.get("update_jobid"):
            Job.params = {"id": update_jobid}
            jobs = await async_attributes(Job, self._access)
            if jobs.get("update_state") != "RUNNING" or not update_available:
                self.system.update(
                    {"update_progress": 0, "update_jobid": 0, "update_state": "unknown"}
                )

        self._is_scale = bool(self.system["version"].startswith("TrueNAS-SCALE-"))

        self._is_virtual = self.system["system_manufacturer"] in [
            "QEMU",
            "VMware, Inc.",
        ] or self.system["system_product"] in ["VirtualBox"]

        if (uptime := self.system["uptime_seconds"]) > 0:
            now = datetime.now().replace(microsecond=0)
            uptime_tm = datetime.timestamp(now - timedelta(seconds=int(uptime)))
            self.system.update(
                {
                    "uptimeEpoch": str(
                        as_local(utc_from_timestamp(uptime_tm)).isoformat()
                    )
                }
            )

        query = [
            {"name": "load"},
            {"name": "cpu"},
            {"name": "arcsize"},
            {"name": "arcratio"},
            {"name": "memory"},
        ]

        if not self._is_virtual:
            query.append({"name": "cputemp"})

        stats: list[dict[str, Any]] = await self.async_get_stats(query)
        for item in stats:
            # CPU temperature
            if item.get("name") == "cputemp" and "aggregations" in item:
                self.system["cpu_temperature"] = round(
                    max(list(filter(None, item["aggregations"]["mean"]))), 1
                )

            # CPU load
            if item.get("name") == "load":
                tmp_arr = ["load_shortterm", "load_midterm", "load_longterm"]
                systemstats_process(self.system, tmp_arr, item, "")

            # CPU usage
            if item.get("name") == "cpu":
                tmp_arr = ["interrupt", "system", "user", "nice", "idle"]
                systemstats_process(self.system, tmp_arr, item, "cpu")
                self.system["cpu_usage"] = round(
                    self.system["cpu_system"] + self.system["cpu_user"], 2
                )

            # arcratio
            if item.get("name") == "memory":
                tmp_arr = [
                    "memory-used_value",
                    "memory-free_value",
                    "memory-cached_value",
                    "memory-buffered_value",
                ]
                systemstats_process(self.system, tmp_arr, item, "memory")
                self.system["memory_total_value"] = round(
                    self.system["memory-used_value"]
                    + self.system["memory-free_value"]
                    + self.system["cache_size-arc_value"],
                    2,
                )
                if (total_value := self.system["memory_total_value"]) > 0:
                    self.system["memory_usage_percent"] = round(
                        100
                        * (float(total_value) - float(self.system["memory-free_value"]))
                        / float(total_value),
                        0,
                    )

            # arcsize
            if item.get("name") == "arcsize":
                tmp_arr = ["cache_size-arc_value", "cache_size-L2_value"]
                systemstats_process(self.system, tmp_arr, item, "memory")

            # arcratio
            if item.get("name") == "arcratio":
                tmp_arr = ["cache_ratio-arc_value", "cache_ratio-L2_value"]
                systemstats_process(self.system, tmp_arr, item, "")

        self.data["systeminfos"] = self.system
        self._sub.notify(Events.SYSTEM.value)
        return self.system

    async def async_get_interfaces(self) -> dict[str, Any]:
        """Get interface info from TrueNAS."""
        self.interfaces = await async_attributes(Interfaces, self._access)
        query = [{"name": "interface", "identifier": uid} for uid in self.interfaces]
        stats = await self.async_get_stats(query)
        for item in stats:
            # Interface
            if (
                item.get("name") == "interface"
                and (identifier := item["identifier"]) in self.interfaces
            ):
                # 12->13 API change
                item["legend"] = [
                    legend.replace("if_octets_", "") for legend in item["legend"]
                ]

                systemstats_process(
                    self.interfaces[identifier], ["rx", "tx"], item, "rx-tx"
                )

        self.data["interfaces"] = self.interfaces
        self._sub.notify(Events.INTERFACES.value)
        return self.interfaces

    async def async_get_stats(self, items: list[dict[str, Any]]) -> Any:
        """Get statistics."""
        query: dict[str, Any] = {
            "graphs": items,
            "reporting_query": {
                "start": "now-90s",
                "end": "now-30s",
                "aggregate": True,
            },
        }

        for param in query["graphs"]:
            if param["name"] in self._systemstats_errored:
                query["graphs"].remove(param)

        stats = []
        try:
            stats = await self._access.async_request(
                "reporting/get_data", method="post", json=query
            )

            if "error" in stats:
                for param in query["graphs"]:
                    await self._access.async_request(
                        "reporting/get_data",
                        method="post",
                        json={
                            "graphs": [param],
                            "reporting_query": {
                                "start": "now-90s",
                                "end": "now-30s",
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
        except TruenasError as error:
            _LOGGER.error(error)

        return stats

    async def async_get_services(self) -> dict[str, Any]:
        """Get service info from TrueNAS."""
        self.services = await async_attributes(Service, self._access)
        for uid, detail in self.services.items():
            self.services[uid]["running"] = detail.get("state") == "RUNNING"
        self.data["services"] = self.services
        self._sub.notify(Events.SERVICES.value)
        return self.services

    async def async_get_pools(self) -> dict[str, Any]:
        """Get pools from TrueNAS."""
        self.pools = await async_attributes(Pool, self._access)
        boot = await async_attributes(Pool, self._access)
        self.pools.update(boot)

        # Process pools
        dataset_available = {}
        dataset_total = {}
        for uid, vals in self.datasets.items():
            if mountpoint := self.datasets[uid].get("mountpoint"):
                available = vals.get("available", 0)
                dataset_available[mountpoint] = b2gib(available)
                dataset_total[mountpoint] = b2gib(available + vals.get("used", 0))

        for uid, vals in self.pools.items():
            if path := dataset_available.get(vals["path"]):
                self.pools[uid]["available_gib"] = path

            if path := dataset_total.get(vals["path"]):
                self.pools[uid]["total_gib"] = path

            if vals["name"] in ["boot-pool", "freenas-boot"]:
                self.pools[uid]["available_gib"] = b2gib(vals["root_dataset_available"])
                self.pools[uid]["total_gib"] = b2gib(
                    vals["root_dataset_available"] + vals["root_dataset_used"]
                )
                self.pools[uid].pop("root_dataset")

        self.data["pools"] = self.pools
        self._sub.notify(Events.POOLS.value)
        return self.pools

    async def async_get_datasets(self) -> dict[str, Any]:
        """Get datasets from TrueNAS."""
        self.datasets = await async_attributes(Datasets, self._access)
        for uid, vals in self.datasets.items():
            self.datasets[uid]["used_gb"] = b2gib(vals.get("used", 0))
        self.data["datasets"] = self.datasets
        self._sub.notify(Events.DATASETS.value)
        return self.datasets

    async def async_get_disks(self) -> dict[str, Any]:
        """Get disks from TrueNAS."""
        self.disks = await async_attributes(Disk, self._access)
        # Get disk temperatures
        temperatures = await self._access.async_request(
            "disk/temperatures", method="post", json={"names": []}
        )
        for uid in self.disks:
            self.disks[uid]["temperature"] = temperatures.get(uid, 0)

        self.data["disks"] = self.disks
        self._sub.notify(Events.DISKS.value)
        return self.disks

    async def async_get_jails(self) -> dict[str, Any] | None:
        """Get jails from TrueNAS."""
        if self._is_scale is False:
            self.jails = await async_attributes(Jail, self._access)
            self.data["jails"] = self.jails
            self._sub.notify(Events.JAILS.value)
            return self.jails
        return None

    async def async_get_virtualmachines(self) -> dict[str, Any]:
        """Get VMs from TrueNAS."""
        self.virtualmachines = await async_attributes(VirtualMachine, self._access)
        for uid, detail in self.virtualmachines.items():
            self.virtualmachines[uid]["running"] = detail.get("state") == "RUNNING"
        self.data["virtualmachines"] = self.virtualmachines
        self._sub.notify(Events.VMS.value)
        return self.virtualmachines

    async def async_get_cloudsync(self) -> dict[str, Any]:
        """Get cloudsync from TrueNAS."""
        self.cloudsync = await async_attributes(CloudSync, self._access)
        self.data["cloudsync"] = self.cloudsync
        self._sub.notify(Events.CLOUD.value)
        return self.cloudsync

    async def async_get_replications(self) -> dict[str, Any]:
        """Get replication from TrueNAS."""
        self.replications = await async_attributes(Replication, self._access)
        self.data["replications"] = self.replications
        self._sub.notify(Events.REPLS.value)
        return self.replications

    async def async_get_snapshottasks(self) -> dict[str, Any]:
        """Get replication from TrueNAS."""
        self.snapshots = await async_attributes(Snapshottask, self._access)
        self.data["snapshots"] = self.snapshots
        self._sub.notify(Events.SNAPS.value)
        return self.snapshots

    async def async_get_charts(self) -> dict[str, Any]:
        """Get Charts from TrueNAS."""
        self.charts = await async_attributes(Charts, self._access)
        for uid, detail in self.charts.items():
            self.charts[uid]["running"] = detail.get("status") == "ACTIVE"
        self.data["charts"] = self.charts
        self._sub.notify(Events.CHARTS.value)
        return self.charts

    async def async_get_smartdisks(self) -> dict[str, Any]:
        """Get smartdisk from TrueNAS."""
        self.smarts = await async_attributes(Smart, self._access)
        self.data["smarts"] = self.smarts
        self._sub.notify(Events.SMARTS.value)
        return self.smarts

    async def async_get_alerts(self) -> dict[str, Any]:
        """Get smartdisk from TrueNAS."""
        self.alerts = await async_attributes(Alerts, self._access)
        self.data["alerts"] = self.alerts
        self._sub.notify(Events.ALERTS.value)
        return self.alerts

    def subscribe(self, _callback: str, *args: Any) -> None:
        """Subscribe event."""
        self._sub.subscribe(_callback, *args)

    def unsubscribe(self, _callback: str, *args: Any) -> None:
        """Unsubscribe event."""
        self._sub.subscribe(_callback, *args)

    async def async_update_all(self) -> dict[str, Any]:
        """Update all datas."""
        for event in Events:
            try:
                if event.name != "ALL":
                    fnc = getattr(self, f"async_get_{event.value}")
                    await fnc()
            except TruenasError as error:
                _LOGGER.error(error)
        self._sub.notify(Events.ALL.value)
        return self.data

    async def async_is_alive(self) -> bool:
        """Check connection."""
        result = await self._access.async_request("core/ping")
        return "pong" in result

    async def async_close(self) -> None:
        """Close open client session."""
        await self._access.async_close()

    async def __aenter__(self) -> Self:
        """Async enter.

        Returns
        -------
            The LaMetricCloud object.
        """
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Async exit.

        Args:
        ----
            _exc_info: Exec type.
        """
        await self.async_close()
