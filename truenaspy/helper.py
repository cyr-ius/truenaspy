"""API parser for JSON APIs."""
from __future__ import annotations

from datetime import datetime
from logging import getLogger
from typing import Any

from pytz import utc

_LOGGER = getLogger(__name__)


def utc_from_timestamp(timestamp: float) -> datetime:
    """Return a UTC time from a timestamp."""
    return utc.localize(datetime.utcfromtimestamp(timestamp))


def b2gib(b: int) -> float:
    """Convert byte to gigabyte."""
    return round(b / 1073741824, 2)


def as_local(dattim: datetime) -> datetime:
    """Convert a UTC datetime object to local time zone."""
    local_timezone = datetime.now().astimezone().tzinfo
    if dattim.tzinfo == local_timezone:
        return dattim
    if dattim.tzinfo is None:
        dattim = utc.localize(dattim)

    return dattim.astimezone(local_timezone)


def from_entry(entry: dict[str, Any], param: str, default=None, reverse=False) -> str:
    """Validate and return str value an API dict."""
    if "/" in param:
        for tmp_param in param.split("/"):
            if isinstance(entry, dict):
                entry = entry.get(tmp_param, default)
        ret = entry
    else:
        ret = entry.get(param, default)

    if isinstance(ret, str):
        if ret in ("on", "On", "ON", "yes", "Yes", "YES", "up", "Up", "UP"):
            return False if reverse else True
        elif ret in ("off", "Off", "OFF", "no", "No", "NO", "down", "Down", "DOWN"):
            return True if reverse else False
        else:
            return str(ret)[:255] if len(str(ret)) > 255 else str(ret)
    elif isinstance(ret, int):
        return int(ret)
    elif isinstance(ret, float):
        return round(float(ret), 2)
    elif isinstance(ret, bool):
        return ret


def parse_api(
    data: dict[str, Any],
    source: dict[str, Any],
    key: str = None,
    vals: dict[str, Any] = None,
) -> dict:
    """Get data from API."""
    if isinstance(source, dict):
        source = [source]

    _LOGGER.debug("Processing source %s", source)

    for entry in source:
        uid = None
        if key:
            if key in entry:
                uid = entry[key]
                if uid not in data:
                    data[uid] = {}
            else:
                continue

        _LOGGER.debug("Processing entry %s", entry)

        for val in vals:
            _name = val["name"]
            _source = val.get("source", _name)
            _convert = val.get("convert")
            _reverse = val.get("reverse", False)
            _default = val.get("default")

            data_name = from_entry(entry, _source, _default, _reverse)

            if _convert == "utc_from_timestamp" and isinstance(data_name, int):
                if data_name > 100000000000:
                    data_name = data_name / 1000
                data_name = utc_from_timestamp(data_name)

            if uid:
                data[uid][_name] = data_name
            else:
                data[_name] = data_name

    return data


def systemstats_process(
    fill_dict: dict[str, Any], arr: list[str], graph: dict[str, Any], mode: str
) -> None:
    """Fill dictionnary from stats."""
    if "aggregations" in graph:
        for item in graph["legend"]:
            if item in arr:
                position = graph["legend"].index(item)
                value = graph["aggregations"]["mean"][position] or 0.0
                if mode == "memory":
                    fill_dict[item] = b2gib(value)
                elif mode == "cpu":
                    fill_dict[f"cpu_{item}"] = round(value, 2)
                elif mode == "rx-tx":
                    fill_dict[item] = round(value / 1024, 2)
                else:
                    fill_dict[item] = round(value, 2)
