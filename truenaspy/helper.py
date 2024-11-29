"""API parser for JSON APIs."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import reduce
from typing import Any


class ExtendedDict(dict[Any, Any]):
    """Extend dictionary class."""

    def getr(self, keys: str, default: Any = None) -> Any:
        """Get recursive attribute."""
        reduce_value: Any = reduce(
            lambda d, key: d.get(key, default) if isinstance(d, dict) else default,
            keys.split("."),
            self,
        )
        if isinstance(reduce_value, dict):
            return ExtendedDict(reduce_value)
        return reduce_value


def utc_from_timestamp(timestamp: float) -> Any:
    """Return a UTC time from a timestamp."""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def b2gib(b: int) -> float | None:
    """Convert byte to gigabyte."""
    if isinstance(b, int):
        return round(b / 1073741824, 2)


def as_local(value: datetime) -> datetime:
    """Convert a UTC datetime object to local time zone."""
    local_timezone = datetime.now().astimezone().tzinfo
    if value.tzinfo == local_timezone:
        return value
    return value.astimezone(local_timezone)


def systemstats_process(
    fill_dict: dict[str, Any],
    arr: list[str],
    graph: dict[str, Any],
    mode: str | None = None,
) -> None:
    """Fill dictionary from stats."""
    if "aggregations" in graph:
        for item in graph["legend"]:
            if item in arr:
                value: int = graph["aggregations"]["mean"].get(item, 0)
                if mode == "memory":
                    fill_dict[f"memory_{item}"] = round(value, 2)
                elif mode == "cpu":
                    fill_dict[f"cpu_{item}"] = round(value, 2)
                elif mode == "rx-tx":
                    fill_dict[item] = round(value / 1024, 2)
                elif mode is not None:
                    fill_dict[f"{mode}_{item}"] = round(value, 2)
                else:
                    fill_dict[item] = round(value, 2)
