"""Class to collect a data."""

from .helper import FieldType, b2gib, utc_from_timestamp


class System:
    """System."""

    attrs = [
        FieldType(name="version"),
        FieldType(name="hostname"),
        FieldType(name="uptime_seconds", default=0),
        FieldType(name="system_serial"),
        FieldType(name="system_product"),
        FieldType(name="system_manufacturer"),
    ]


class Update:
    """Update."""

    attrs = [
        FieldType(name="job_id", default=0),
        FieldType(name="status", source="status"),
        FieldType(name="version", source="version"),
        FieldType(name="progress", default=0),
        FieldType(
            name="available", source="status", evaluation=lambda x: x == "AVAILABLE"
        ),
    ]


class Job:
    """Job."""

    attrs = [
        FieldType(name="progress", source="progress.percent", default=0),
        FieldType(name="state", source="state"),
    ]


class Interfaces:
    """Interfaces."""

    attrs = [
        FieldType(name="id"),
        FieldType(name="name"),
        FieldType(name="description"),
        FieldType(name="mtu"),
        FieldType(name="link_state", source="state.link_state"),
        FieldType(name="active_media_type", source="state.active_media_type"),
        FieldType(name="link_address", source="state.link_address"),
    ]


class Service:
    """Service."""

    attrs = [
        FieldType(name="id"),
        FieldType(name="service"),
        FieldType(name="enable", default=False),
        FieldType(name="state"),
        FieldType(name="running", source="state", evaluation=lambda x: x == "RUNNING"),
    ]


class Pool:
    """Pool."""

    attrs = [
        FieldType(name="autotrim", default=False, source="autotrim.parsed"),
        FieldType(name="guid", default=0),
        FieldType(name="healthy", default=False),
        FieldType(name="id", default=0),
        FieldType(name="is_decrypted", default=False),
        FieldType(name="name"),
        FieldType(name="path"),
        FieldType(name="scan_function", source="scan.function"),
        FieldType(name="scan_function", source="scan.state"),
        FieldType(name="status"),
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


class Boot:
    """Boot."""

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


class Disk:
    """Disk."""

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


class Jail:
    """Jail."""

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


class VirtualMachine:
    """VirtualMachine."""

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
        FieldType(
            name="running", source="status.state", evaluation=lambda x: x == "RUNNING"
        ),
    ]


class Datasets:
    """Datasets."""

    attrs = [
        FieldType(name="atime", default=False, source="atime.parsed"),
        FieldType(name="available", default=0, source="available.parsed"),
        FieldType(name="casesensitivity", source="casesensitivity.parsed"),
        FieldType(name="checksum", source="checksum.parsed"),
        FieldType(name="comments", default="", source="comments.parsed"),
        FieldType(name="compression", source="compression.parsed"),
        FieldType(name="copies", default=0, source="copies.parsed"),
        FieldType(name="deduplication", default=False, source="deduplication.parsed"),
        FieldType(name="encrypted", default=False),
        FieldType(name="encryption_algorithm", source="encryption_algorithm.parsed"),
        FieldType(name="exec", default=False, source="exec.parsed"),
        FieldType(name="id"),
        FieldType(name="locked"),
        FieldType(name="mountpoint"),
        FieldType(name="name"),
        FieldType(name="pool"),
        FieldType(name="quota", source="quota.parsed"),
        FieldType(name="readonly", default=False, source="readonly.parsed"),
        FieldType(name="recordsize", default=0, source="recordsize.parsed"),
        FieldType(name="sync", source="sync.parsed"),
        FieldType(name="type"),
        FieldType(name="used", default=0, source="used.parsed"),
        FieldType(
            name="used_gb",
            source="used.parsed",
            evaluation=lambda x: 0 if not x else b2gib(x),
        ),
    ]


class CloudSync:
    """CloudSync."""

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


class Replication:
    """Replication."""

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


class Snapshottask:
    """Snapshottask."""

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


class Charts:
    """Charts."""

    attrs = [
        FieldType(name="id", default=0),
        FieldType(name="name"),
        FieldType(name="description", source="chart_metadata.description"),
        FieldType(name="meta_version", source="chart_metadata.version"),
        FieldType(name="meta_app_version", source="chart_metadata.appVersion"),
        FieldType(
            name="meta_latests_version", source="chart_metadata.latest_chart_version"
        ),
        FieldType(name="human_version"),
        FieldType(name="human_latest_version"),
        FieldType(name="update_available"),
        FieldType(name="container_images_update_available"),
        FieldType(
            name="portal",
            source="portals.open",
            evaluation=lambda x: x[0] if isinstance(x, list) and len(x) > 0 else None,
        ),
        FieldType(name="status"),
        FieldType(name="running", source="status", evaluation=lambda x: x == "ACTIVE"),
    ]


class Smart:
    """Smart."""

    attrs = [
        FieldType(name="name"),
        FieldType(name="serial"),
        FieldType(name="model"),
        FieldType(name="zfs_guid"),
        FieldType(name="devname"),
        FieldType(
            name="status",
            source="tests",
            default=False,
            evaluation=lambda x: x[0].get("status") != "SUCCESS"
            if isinstance(x, list) and len(x) > 0
            else False,
        ),
    ]


class Alerts:
    """Alerts."""

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


class Rsync:
    """Rsync."""

    attrs = [
        FieldType(name="id"),
        FieldType(name="desc"),
    ]
