"""Class to collect a data."""
from .helper import Collects, FieldType, utc_from_timestamp


class System(Collects):
    """System."""

    request = "system/info"
    attrs = [
        FieldType(name="version"),
        FieldType(name="hostname"),
        FieldType(name="uptime_seconds", default=0),
        FieldType(name="system_serial"),
        FieldType(name="system_product"),
        FieldType(name="system_manufacturer"),
    ]


class Update(Collects):
    """System."""

    request = "update/check_available"
    method = "post"
    attrs = [
        FieldType(name="update_status", source="status"),
        FieldType(name="update_version", source="version"),
    ]


class Job(Collects):
    """System."""

    request = "core/get_jobs"
    method = "post"
    attrs = [
        FieldType(name="update_progress", source="progress.percent", default=0),
        FieldType(name="update_state", source="state"),
    ]


class Interfaces(Collects):
    """System."""

    request = "interface"
    key = "name"
    attrs = [
        FieldType(name="id"),
        FieldType(name="name"),
        FieldType(name="description"),
        FieldType(name="mtu"),
        FieldType(name="link_state", source="state.link_state"),
        FieldType(name="active_media_type", source="state.active_media_type"),
        FieldType(name="link_address", source="state.link_address"),
    ]


class Service(Collects):
    """Service."""

    request = "service"
    key = "service"
    attrs = [
        FieldType(name="id"),
        FieldType(name="service"),
        FieldType(name="enable", default=False),
        FieldType(name="state"),
    ]


class Pool(Collects):
    """Pool."""

    request = "pool"
    key = "guid"
    attrs = [
        FieldType(name="guid", default=0),
        FieldType(name="id", default=0),
        FieldType(name="name"),
        FieldType(name="path"),
        FieldType(name="status"),
        FieldType(name="healthy", default=False),
        FieldType(name="is_decrypted", default=False),
        FieldType(name="autotrim", default=False, source="autotrim.parsed"),
        FieldType(name="scan_function", source="scan.function"),
        FieldType(name="scan_function", source="scan.state"),
        FieldType(
            name="scrub_start",
            source="scan.start_time.$date",
            default=0,
            evaluation=lambda x: utc_from_timestamp(
                x if x < 100000000000 else x / 1000
            ),
        ),
        FieldType(
            name="scrub_end",
            source="scan.end_time.$date",
            default=0,
            evaluation=lambda x: utc_from_timestamp(
                x if x < 100000000000 else x / 1000
            ),
        ),
        FieldType(name="scrub_secs_left", default=0, source="scan.total_secs_left"),
    ]


class Boot(Collects):
    """Boot."""

    request = "boot/get_state"
    key = "guid"
    attrs = [
        FieldType(name="guid", default=0),
        FieldType(name="id", default=0),
        FieldType(name="name"),
        FieldType(name="path"),
        FieldType(name="status"),
        FieldType(name="healthy", default=False),
        FieldType(name="is_decrypted", default=False),
        FieldType(name="autotrim", default=False, source="autotrim.parsed"),
        FieldType(name="root_dataset"),
        FieldType(
            name="root_dataset_available",
            default=0,
            source="root_dataset.properties.available.parsed",
        ),
        FieldType(
            name="root_dataset_used",
            default=0,
            source="root_dataset.properties.used.parsed",
        ),
        FieldType(name="scan_function", source="scan.function"),
        FieldType(name="scan_function", source="scan.state"),
        FieldType(
            name="scrub_start",
            source="scan.start_time.$date",
            default=0,
            evaluation=lambda x: utc_from_timestamp(
                x if x < 100000000000 else x / 1000
            ),
        ),
        FieldType(
            name="scrub_end",
            source="scan.end_time.$date",
            default=0,
            evaluation=lambda x: utc_from_timestamp(
                x if x < 100000000000 else x / 1000
            ),
        ),
        FieldType(name="scrub_secs_left", default=0, source="scan.total_secs_left"),
    ]


class Disk(Collects):
    """Disk."""

    request = "disk"
    key = "devname"
    attrs = [
        FieldType(name="name"),
        FieldType(name="devname"),
        FieldType(name="serial"),
        FieldType(name="size"),
        FieldType(name="hddstandby_force", default=False),
        FieldType(name="advpowermgmt"),
        FieldType(name="acousticlevel"),
        FieldType(name="togglesmart", default=False),
        FieldType(name="model"),
        FieldType(name="rotationrate"),
        FieldType(name="type"),
    ]


class Jail(Collects):
    """Jail."""

    request = "jail"
    key = "id"
    attrs = [
        FieldType(name="id"),
        FieldType(name="comment"),
        FieldType(name="host_hostname"),
        FieldType(name="jail_zfs_dataset"),
        FieldType(name="last_started"),
        FieldType(name="ip4_addr"),
        FieldType(name="ip6_addr"),
        FieldType(name="release"),
        FieldType(name="state", default=False),
        FieldType(name="type"),
        FieldType(name="plugin_name"),
    ]


class VirtualMachine(Collects):
    """VirtualMachine."""

    request = "vm"
    key = "name"
    attrs = [
        FieldType(name="id", default=0),
        FieldType(name="name"),
        FieldType(name="description"),
        FieldType(name="vcpus", default=0),
        FieldType(name="memory", default=0),
        FieldType(name="autostart", default=False),
        FieldType(name="cores", default=0),
        FieldType(name="threads", default=0),
        FieldType(name="state", source="status.state"),
    ]


class Datasets(Collects):
    """Datasets."""

    request = "pool/dataset"
    key = "id"
    attrs = [
        FieldType(name="id"),
        FieldType(name="type"),
        FieldType(name="name"),
        FieldType(name="pool"),
        FieldType(name="mountpoint"),
        FieldType(name="comments", default="", source="comments.parsed"),
        FieldType(name="deduplication", default=False, source="deduplication.parsed"),
        FieldType(name="atime", default=False, source="atime.parsed"),
        FieldType(name="casesensitivity", source="casesensitivity.parsed"),
        FieldType(name="checksum", source="checksum.parsed"),
        FieldType(name="exec", default=False, source="exec.parsed"),
        FieldType(name="sync", source="sync.parsed"),
        FieldType(name="compression", source="compression.parsed"),
        FieldType(name="quota", source="quota.parsed"),
        FieldType(name="copies", default=0, source="copies.parsed"),
        FieldType(name="readonly", default=False, source="readonly.parsed"),
        FieldType(name="recordsize", default=0, source="recordsize.parsed"),
        FieldType(name="encryption_algorithm", source="encryption_algorithm.parsed"),
        FieldType(name="used", default=0, source="used.parsed"),
        FieldType(name="available", default=0, source="available.parsed"),
    ]


class CloudSync(Collects):
    """CloudSync."""

    request = "cloudsync"
    key = "id"
    attrs = [
        FieldType(name="id"),
        FieldType(name="description"),
        FieldType(name="direction"),
        FieldType(name="path"),
        FieldType(name="enabled", default=False),
        FieldType(name="transfer_mode"),
        FieldType(name="snapshot", default=False),
        FieldType(name="state", source="job.state"),
        FieldType(
            name="time_started",
            source="job.time_started.$date",
            default=0,
            evaluation=lambda x: utc_from_timestamp(
                x if x < 100000000000 else x / 1000
            ),
        ),
        FieldType(
            name="time_finished",
            source="job.time_finished.$date",
            default=0,
            evaluation=lambda x: utc_from_timestamp(
                x if x < 100000000000 else x / 1000
            ),
        ),
        FieldType(name="job_percent", source="job.progress.percent", default=0),
        FieldType(name="job.progress.percent", source="job.progress.description"),
    ]


class Replication(Collects):
    """Replication."""

    request = "replication"
    key = "name"
    attrs = [
        FieldType(name="id", default=0),
        FieldType(name="name"),
        FieldType(name="source_datasets"),
        FieldType(name="target_dataset"),
        FieldType(name="recursive", default=False),
        FieldType(name="enabled", default=False),
        FieldType(name="direction"),
        FieldType(name="transport"),
        FieldType(name="auto", default=False),
        FieldType(name="retention_policy"),
        FieldType(name="state", source="job.state"),
        FieldType(
            name="time_started",
            source="job.time_started.$date",
            default=0,
            evaluation=lambda x: utc_from_timestamp(
                x if x < 100000000000 else x / 1000
            ),
        ),
        FieldType(
            name="time_finished",
            source="job.time_finished.$date",
            default=0,
            evaluation=lambda x: utc_from_timestamp(
                x if x < 100000000000 else x / 1000
            ),
        ),
        FieldType(name="job_percent", source="job.progress.percent", default=0),
        FieldType(name="job.progress.percent", source="job.progress.description"),
    ]


class Snapshottask(Collects):
    """Snapshottask."""

    request = "pool/snapshottask"
    key = "id"
    attrs = [
        FieldType(name="id", default=0),
        FieldType(name="dataset"),
        FieldType(name="recursive", default=False),
        FieldType(name="lifetime_value", default=0),
        FieldType(name="lifetime_unit"),
        FieldType(name="enabled", default=False),
        FieldType(name="naming_schema"),
        FieldType(name="allow_empty", default=False),
        FieldType(name="vmware_sync", default=False),
        FieldType(name="state", source="state.state"),
        FieldType(
            name="datetime",
            source="state.datetime.$date",
            default=0,
            evaluation=lambda x: utc_from_timestamp(
                x if x < 100000000000 else x / 1000
            ),
        ),
        FieldType(
            name="time_finished",
            source="job.time_finished.$date",
            default=0,
            evaluation=lambda x: utc_from_timestamp(
                x if x < 100000000000 else x / 1000
            ),
        ),
        FieldType(name="job_percent", source="job.progress.percent", default=0),
        FieldType(name="job.progress.percent", source="job.progress.description"),
    ]


class Charts(Collects):
    """Charts."""

    request = "chart/release"
    key = "id"
    attrs = [
        FieldType(name="id", default=0),
        FieldType(name="name"),
        FieldType(name="human_version"),
        FieldType(name="update_available"),
        FieldType(name="container_images_update_available"),
        FieldType(name="portal", source="portals.open"),
        FieldType(name="status"),
    ]


class Smart(Collects):
    """Smart."""

    request = "/smart/test/results"
    key = "name"
    params = {"offset": 1}
    attrs = [
        FieldType(name="name"),
        FieldType(name="serial"),
        FieldType(name="model"),
        FieldType(name="zfs_guid"),
        FieldType(name="devname"),
        FieldType(
            name="smartdisk",
            source="tests",
            evaluation=lambda x: x[0].get("status")
            if isinstance(x, list) and len(x) > 0
            else "n/a",
        ),
    ]


class Alerts(Collects):
    """Alerts."""

    request = "/alert/list"
    key = "uuid"
    attrs = [
        FieldType(name="uuid"),
        FieldType(name="formatted"),
        FieldType(name="klass"),
        FieldType(name="level"),
        FieldType(
            name="date_created",
            source="datetime.$date",
            evaluation=lambda x: utc_from_timestamp(
                x if x < 100000000000 else x / 1000
            ),
        ),
        FieldType(
            name="last_occurrence",
            source="last_occurrence.$date",
            evaluation=lambda x: utc_from_timestamp(
                x if x < 100000000000 else x / 1000
            ),
        ),
    ]
