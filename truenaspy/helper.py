"""API parser for JSON APIs."""

from __future__ import annotations

from datetime import datetime
from functools import reduce
import json
from logging import getLogger
from typing import Any, Callable, Type

from pytz import utc  # type: ignore[import-untyped]

_LOGGER = getLogger(__name__)


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


class FieldType(dict[str, Any]):
    """Attributes fields."""

    name: str
    default: Any = None
    source: str | None = None
    evaluation: Callable[..., Any] | None = None


def utc_from_timestamp(timestamp: float) -> Any:
    """Return a UTC time from a timestamp."""
    return utc.localize(datetime.utcfromtimestamp(timestamp))


def b2gib(b: int) -> float | None:
    """Convert byte to gigabyte."""
    if isinstance(b, int):
        return round(b / 1073741824, 2)


def as_local(dattim: datetime) -> datetime:
    """Convert a UTC datetime object to local time zone."""
    local_timezone = datetime.now().astimezone().tzinfo
    if dattim.tzinfo == local_timezone:
        return dattim
    if dattim.tzinfo is None:
        dattim = utc.localize(dattim)

    return dattim.astimezone(local_timezone)


def json_loads(response: str | bytes) -> Any:
    """Json load."""

    def _float_parser(val: float | Any | None) -> float | None:
        if val:
            return round(float(val), 2)
        return None

    def _parser(obj: dict[str, Any]) -> ExtendedDict:
        """parse json."""
        for key, val in obj.items():
            if val in ("on", "On", "ON", "yes", "Yes", "YES", "up", "Up", "UP"):
                obj[key] = True
            if val in ("off", "Off", "OFF", "no", "No", "NO", "down", "Down", "DOWN"):
                obj[key] = True
        return ExtendedDict(obj)

    return json.loads(response, object_hook=_parser, parse_float=_float_parser)


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


def search_attrs(identity: Type[Any], dataref: Any) -> Any:
    """Map attributes."""
    attributes: list[dict[str, Any]] | dict[str, Any] = []
    if dataref is not None and identity.attrs:
        if not isinstance(dataref, list):
            attributes = {}
            dataref = [dataref]
        for item in dataref:
            attrs = {}
            for attr in identity.attrs:
                name = attr["name"]
                key = attr.get("source", name)
                value = item.getr(key, attr.get("default"))
                if value and (evaluation := attr.get("evaluation")):
                    try:
                        value = evaluation(value)
                    except Exception as error:  # pylint: disable=broad-except
                        _LOGGER.error(error)
                attrs.update({name: value})
            if isinstance(attributes, list):
                attributes.append(attrs)
            else:
                attributes.update(attrs)

    return attributes
