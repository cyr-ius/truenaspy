"""TrueNAS API."""
from __future__ import annotations

from datetime import datetime, timedelta
from logging import getLogger
from typing import Any, Callable

from aiohttp import ClientSession

from .auth import TrueNASConnect
from .helper import as_local, b2gib, parse_api, systemstats_process, utc_from_timestamp
from .subscription import Events, Subscriptions

_LOGGER = getLogger(__name__)


class TrueNASAPI(object):
    """Handle all communication with TrueNAS."""

    def __init__(
        self,
        host: str,
        token: str,
        session: ClientSession | None = None,
        use_ssl: bool = False,
        verify_ssl: bool = True,
        scan_intervall: int = 60,
    ) -> None:
        """Initialize the TrueNAS API."""
        self.session = session if session else ClientSession()
        self._access = TrueNASConnect(self.session, host, token, use_ssl, verify_ssl)
        self._is_scale: bool = False
        self._is_virtual: bool = False
        self._sub = Subscriptions(
            (self.async_update_all, self.async_is_alive), scan_intervall
        )
        self._systemstats_errored: list(str) = []
        self.system = {}
        self.interfaces = {}
        self.stats = {}
        self.services = {}
        self.pools = {}
        self.datasets = {}
        self.disks = {}
        self.jails = {}
        self.virtualmachines = {}
        self.cloudsync = {}
        self.replications = {}
        self.snapshots = {}
        self.charts = {}
        self.data: dict[str, Any] = {}

    async def async_get_system(self) -> None:
        """Get system info from TrueNAS."""
        source = await self._access.async_request("system/info")
        self.system = parse_api(
            data={},
            source=source,
            vals=[
                {"name": "version"},
                {"name": "hostname"},
                {"name": "uptime_seconds", "default": 0},
                {"name": "system_serial"},
                {"name": "system_product"},
                {"name": "system_manufacturer"},
            ],
        )

        source = await self._access.async_request(
            "update/check_available", method="post"
        )
        update = parse_api(
            data={},
            source=source,
            vals=[
                {"name": "update_status", "source": "status"},
                {"name": "update_version", "source": "version"},
            ],
        )

        # update_available
        update_available = update.get("update_status") == "AVAILABLE"
        self.system.update({"update_available": update_available})
        # update_version
        if not update_available:
            self.system.update({"update_version": self.system["version"]})

        if update_jobid := self.system.get("update_jobid"):
            source = self._access.async_request(
                "core/get_jobs", params={"id": update_jobid}
            )
            jobs = parse_api(
                data={},
                source=source,
                vals=[
                    {
                        "name": "update_progress",
                        "source": "progress/percent",
                        "default": 0,
                    },
                    {"name": "update_state", "source": "state"},
                ],
            )

            if jobs["update_state"] != "RUNNING" or not update_available:
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

        stats = await self.async_get_stats(query)
        for item in stats:
            # CPU temperature
            if item.get("name") == "cputemp" and "aggregations" in item:
                self.system["cpu_temperature"] = round(
                    max(list(filter(None, item["aggregations"]["mean"]))), 1
                )

            # CPU load
            if item.get("name") == "load":
                tmp_arr = ("load_shortterm", "load_midterm", "load_longterm")
                systemstats_process(self.system, tmp_arr, item, "")

            # CPU usage
            if item.get("name") == "cpu":
                tmp_arr = ("interrupt", "system", "user", "nice", "idle")
                systemstats_process(self.system, tmp_arr, item, "cpu")
                self.system["cpu_usage"] = round(
                    self.system["cpu_system"] + self.system["cpu_user"], 2
                )

            # arcratio
            if item.get("name") == "memory":
                tmp_arr = (
                    "memory-used_value",
                    "memory-free_value",
                    "memory-cached_value",
                    "memory-buffered_value",
                )
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
                tmp_arr = ("cache_size-arc_value", "cache_size-L2_value")
                systemstats_process(self.system, tmp_arr, item, "memory")

            # arcratio
            if item.get("name") == "arcratio":
                tmp_arr = ("cache_ratio-arc_value", "cache_ratio-L2_value")
                systemstats_process(self.system, tmp_arr, item, "")

        self.data["systeminfos"] = self.system
        self._sub.notify(Events.SYSTEM)
        return self.system

    async def async_get_interfaces(self) -> None:
        """Get interface info from TrueNAS."""
        source = await self._access.async_request("interface")
        self.interfaces = parse_api(
            data={},
            source=source,
            key="name",
            vals=[
                {"name": "id"},
                {"name": "name"},
                {"name": "description"},
                {"name": "mtu"},
                {"name": "link_state", "source": "state/link_state"},
                {"name": "active_media_type", "source": "state/active_media_type"},
                {
                    "name": "active_media_subtype",
                    "source": "state/active_media_subtype",
                },
                {"name": "link_address", "source": "state/link_address"},
            ],
        )

        query = [
            {"name": "interface", "identifier": uid} for uid in self.interfaces.keys()
        ]
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
                    self.interfaces[identifier], ("rx", "tx"), item, "rx-tx"
                )

        self.data["interfaces"] = self.interfaces
        self._sub.notify(Events.INTERFACES)
        return self.interfaces

    async def async_get_stats(self, items: list[dict[str, Any]]) -> None:
        """Get statistics."""
        query = {
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

        stats = await self._access.async_request(
            "reporting/get_data", method="post", json=query
        )

        if not isinstance(stats, list):
            if "error" in stats:
                for param in query["graphs"]:
                    graph_retry = await self._access.async_request(
                        "reporting/get_data",
                        method="post",
                        json={
                            "graphs": [
                                param,
                            ],
                            "reporting_query": {
                                "start": "now-90s",
                                "end": "now-30s",
                                "aggregate": True,
                            },
                        },
                    )
                    if not isinstance(graph_retry, list) and "error" in stats:
                        self._systemstats_errored.append(param["name"])

                _LOGGER.warning(
                    "Fetching following graphs failed, check your NAS: %s",
                    self._systemstats_errored,
                )
                await self.async_get_stats(items)

        return stats

    async def async_get_services(self) -> None:
        """Get service info from TrueNAS."""
        source = await self._access.async_request("service")
        self.services = parse_api(
            data={},
            source=source,
            key="service",
            vals=[
                {"name": "id", "default": 0},
                {"name": "service"},
                {"name": "enable", "default": False},
                {"name": "state"},
            ],
        )

        for uid, detail in self.services.items():
            self.services[uid]["running"] = detail.get("state") == "RUNNING"

        self.data["services"] = self.services
        self._sub.notify(Events.SERVICES)
        return self.services

    async def async_get_pools(self) -> None:
        """Get pools from TrueNAS."""
        source = await self._access.async_request("pool")
        self.pools = parse_api(
            data={},
            source=source,
            key="guid",
            vals=[
                {"name": "guid", "default": 0},
                {"name": "id", "default": 0},
                {"name": "name"},
                {"name": "path"},
                {"name": "status"},
                {"name": "healthy", "default": False},
                {"name": "is_decrypted", "default": False},
                {"name": "autotrim", "source": "autotrim/parsed", "default": False},
                {"name": "scan_function", "source": "scan/function"},
                {"name": "scrub_state", "source": "scan/state"},
                {
                    "name": "scrub_start",
                    "source": "scan/start_time/$date",
                    "default": 0,
                    "convert": "utc_from_timestamp",
                },
                {
                    "name": "scrub_end",
                    "source": "scan/end_time/$date",
                    "default": 0,
                    "convert": "utc_from_timestamp",
                },
                {
                    "name": "scrub_secs_left",
                    "source": "scan/total_secs_left",
                    "default": 0,
                },
            ],
        )

        source = await self._access.async_request("boot/get_state")
        self.pools = parse_api(
            data=self.pools,
            source=source,
            key="guid",
            vals=[
                {"name": "guid", "default": 0},
                {"name": "id", "default": 0},
                {"name": "name"},
                {"name": "path"},
                {"name": "status"},
                {"name": "healthy", "default": False},
                {"name": "is_decrypted", "default": False},
                {"name": "autotrim", "source": "autotrim/parsed", "default": False},
                {"name": "root_dataset"},
                {
                    "name": "root_dataset_available",
                    "source": "root_dataset/properties/available/parsed",
                    "default": 0,
                },
                {
                    "name": "root_dataset_used",
                    "source": "root_dataset/properties/used/parsed",
                    "default": 0,
                },
                {"name": "scan_function", "source": "scan/function"},
                {"name": "scrub_state", "source": "scan/state"},
                {
                    "name": "scrub_start",
                    "source": "scan/start_time/$date",
                    "default": 0,
                    "convert": "utc_from_timestamp",
                },
                {
                    "name": "scrub_end",
                    "source": "scan/end_time/$date",
                    "default": 0,
                    "convert": "utc_from_timestamp",
                },
                {
                    "name": "scrub_secs_left",
                    "source": "scan/total_secs_left",
                    "default": 0,
                },
            ],
        )

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
        self._sub.notify(Events.POOLS)
        return self.pools

    async def async_get_datasets(self) -> None:
        """Get datasets from TrueNAS."""
        source = await self._access.async_request("pool/dataset")
        self.datasets = parse_api(
            data={},
            source=source,
            key="id",
            vals=[
                {"name": "id"},
                {"name": "type"},
                {"name": "name"},
                {"name": "pool"},
                {"name": "mountpoint"},
                {"name": "comments", "source": "comments/parsed", "default": ""},
                {
                    "name": "deduplication",
                    "source": "deduplication/parsed",
                    "default": False,
                },
                {"name": "atime", "source": "atime/parsed", "default": False},
                {"name": "casesensitivity", "source": "casesensitivity/parsed"},
                {"name": "checksum", "source": "checksum/parsed"},
                {"name": "exec", "source": "exec/parsed", "default": False},
                {"name": "sync", "source": "sync/parsed"},
                {"name": "compression", "source": "compression/parsed"},
                {"name": "compressratio", "source": "compressratio/parsed"},
                {"name": "quota", "source": "quota/parsed"},
                {"name": "copies", "source": "copies/parsed", "default": 0},
                {"name": "readonly", "source": "readonly/parsed", "default": False},
                {"name": "recordsize", "source": "recordsize/parsed", "default": 0},
                {
                    "name": "encryption_algorithm",
                    "source": "encryption_algorithm/parsed",
                },
                {"name": "used", "source": "used/parsed", "default": 0},
                {"name": "available", "source": "available/parsed", "default": 0},
            ],
        )

        for uid, vals in self.datasets.items():
            self.datasets[uid]["used_gb"] = b2gib(vals.get("used", 0))

        self.data["datasets"] = self.datasets
        self._sub.notify(Events.DATASETS)
        return self.datasets

    async def async_get_disks(self) -> None:
        """Get disks from TrueNAS."""
        source = await self._access.async_request("disk")
        self.disks = parse_api(
            data={},
            source=source,
            key="devname",
            vals=[
                {"name": "name"},
                {"name": "devname"},
                {"name": "serial"},
                {"name": "size"},
                {"name": "hddstandby"},
                {"name": "hddstandby_force", "default": False},
                {"name": "advpowermgmt"},
                {"name": "acousticlevel"},
                {"name": "togglesmart", "default": False},
                {"name": "model"},
                {"name": "rotationrate"},
                {"name": "type"},
            ],
        )

        # Get disk temperatures
        temperatures = await self._access.async_request(
            "disk/temperatures", method="post", json={"names": []}
        )
        for uid in self.disks:
            self.disks[uid]["temperature"] = temperatures.get(uid, 0)

        self.data["disks"] = self.disks
        self._sub.notify(Events.DISKS)
        return self.disks

    async def async_get_jails(self) -> None:
        """Get jails from TrueNAS."""
        if self._is_scale is False:
            source = await self._access.async_request("jail")
            self.jails = parse_api(
                data={},
                source=source,
                key="id",
                vals=[
                    {"name": "id"},
                    {"name": "comment"},
                    {"name": "host_hostname"},
                    {"name": "jail_zfs_dataset"},
                    {"name": "last_started"},
                    {"name": "ip4_addr"},
                    {"name": "ip6_addr"},
                    {"name": "release"},
                    {"name": "state", "default": False},
                    {"name": "type"},
                    {"name": "plugin_name"},
                ],
            )
            self.data["jails"] = self.jails
            self._sub.notify(Events.JAILS)
            return self.jails

    async def async_get_virtualmachines(self) -> None:
        """Get VMs from TrueNAS."""
        source = await self._access.async_request("vm")
        self.virtualmachines = parse_api(
            data={},
            source=source,
            key="name",
            vals=[
                {"name": "id", "default": 0},
                {"name": "name"},
                {"name": "description"},
                {"name": "vcpus", "default": 0},
                {"name": "memory", "default": 0},
                {"name": "autostart", "default": False},
                {"name": "cores", "default": 0},
                {"name": "threads", "default": 0},
                {"name": "state", "source": "status/state"},
            ],
        )

        for uid, detail in self.virtualmachines.items():
            self.virtualmachines[uid]["running"] = detail.get("state") == "RUNNING"

        self.data["virtualmachines"] = self.virtualmachines
        self._sub.notify(Events.VMS)
        return self.virtualmachines

    async def async_get_cloudsync(self) -> None:
        """Get cloudsync from TrueNAS."""
        source = await self._access.async_request("cloudsync")
        self.cloudsync = parse_api(
            data={},
            source=source,
            key="id",
            vals=[
                {"name": "id"},
                {"name": "description"},
                {"name": "direction"},
                {"name": "path"},
                {"name": "enabled", "default": False},
                {"name": "transfer_mode"},
                {"name": "snapshot", "default": False},
                {"name": "state", "source": "job/state"},
                {
                    "name": "time_started",
                    "source": "job/time_started/$date",
                    "default": 0,
                    "convert": "utc_from_timestamp",
                },
                {
                    "name": "time_finished",
                    "source": "job/time_finished/$date",
                    "default": 0,
                    "convert": "utc_from_timestamp",
                },
                {"name": "job_percent", "source": "job/progress/percent", "default": 0},
                {"name": "job_description", "source": "job/progress/description"},
            ],
        )
        self.data["cloudsync"] = self.cloudsync
        self._sub.notify(Events.CLOUD)
        return self.cloudsync

    async def async_get_replications(self) -> None:
        """Get replication from TrueNAS."""
        source = await self._access.async_request("replication")
        self.replications = parse_api(
            data={},
            source=source,
            key="name",
            vals=[
                {"name": "id", "default": 0},
                {"name": "name"},
                {"name": "source_datasets"},
                {"name": "target_dataset"},
                {"name": "recursive", "default": False},
                {"name": "enabled", "default": False},
                {"name": "direction"},
                {"name": "transport"},
                {"name": "auto", "default": False},
                {"name": "retention_policy"},
                {"name": "state", "source": "job/state"},
                {
                    "name": "time_started",
                    "source": "job/time_started/$date",
                    "default": 0,
                    "convert": "utc_from_timestamp",
                },
                {
                    "name": "time_finished",
                    "source": "job/time_finished/$date",
                    "default": 0,
                    "convert": "utc_from_timestamp",
                },
                {"name": "job_percent", "source": "job/progress/percent", "default": 0},
                {"name": "job_description", "source": "job/progress/description"},
            ],
        )

        self.data["replications"] = self.replications
        self._sub.notify(Events.REPLS)
        return self.replications

    async def async_get_snapshottasks(self) -> None:
        """Get replication from TrueNAS."""
        source = await self._access.async_request("pool/snapshottask")
        self.snapshots = parse_api(
            data={},
            source=source,
            key="id",
            vals=[
                {"name": "id", "default": 0},
                {"name": "dataset"},
                {"name": "recursive", "default": False},
                {"name": "lifetime_value", "default": 0},
                {"name": "lifetime_unit"},
                {"name": "enabled", "default": False},
                {"name": "naming_schema"},
                {"name": "allow_empty", "default": False},
                {"name": "vmware_sync", "default": False},
                {"name": "state", "source": "state/state"},
                {
                    "name": "datetime",
                    "source": "state/datetime/$date",
                    "default": 0,
                    "convert": "utc_from_timestamp",
                },
            ],
        )
        self.data["snapshots"] = self.snapshots
        self._sub.notify(Events.SNAPS)
        return self.snapshots

    async def async_get_charts(self) -> None:
        """Get Charts from TrueNAS."""
        source = await self._access.async_request("chart/release")
        self.charts = parse_api(
            data={},
            source=source,
            key="id",
            vals=[
                {"name": "id", "default": 0},
                {"name": "name"},
                {"name": "human_version"},
                {"name": "update_available"},
                {"name": "container_images_update_available"},
                {"name": "portal", "source": "portals/open"},
                {"name": "status"},
            ],
        )
        for uid, detail in self.charts.items():
            self.charts[uid]["running"] = detail.get("status") == "ACTIVE"

        self.data["charts"] = self.charts
        self._sub.notify(Events.CHARTS)
        return self.charts

    def subscribe(self, _callback: Callable, *args: Any):
        """Subscribe event."""
        self._sub.subscribe(_callback, *args)

    def unsubscribe(self, _callback: Callable, *args: Any):
        """Unsubscribe event."""
        self._sub.subscribe(_callback, *args)

    async def async_close(self) -> None:
        """Close session."""
        await self.session.close()

    async def async_update_all(self) -> None:
        """Update all datas."""
        await self.async_get_system()
        await self.async_get_interfaces()
        await self.async_get_services()
        await self.async_get_datasets()
        await self.async_get_pools()
        await self.async_get_disks()
        await self.async_get_jails()
        await self.async_get_virtualmachines()
        await self.async_get_cloudsync()
        await self.async_get_replications()
        await self.async_get_snapshottasks()
        await self.async_get_charts()
        self._sub.notify(Events.ALL)
        return self.data

    async def async_is_alive(self) -> bool:
        """Check connection."""
        result = await self._access.async_request("core/ping")
        if "pong" not in result:
            return False
        return True
