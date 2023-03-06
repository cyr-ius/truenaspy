"""TrueNAS API Subscription."""
from __future__ import annotations

import asyncio
import time
from enum import Enum
from logging import getLogger
from typing import Callable, Dict, List, Tuple

_LOGGER = getLogger(__name__)


class Events(Enum):
    """Subscription events."""

    SYSTEM = "system"
    INTERFACES = "interfaces"
    SERVICES = "services"
    DATASETS = "datasets"
    POOLS = "pools"
    DISKS = "disks"
    JAILS = "jails"
    VMS = "vms"
    CHARTS = "charts"
    CLOUD = "cloudsync"
    REPLS = "replications"
    SNAPS = "snapshottasks"
    ALL = "all_events"


class Subscriptions:
    """Store subscriptions."""

    def __init__(self, api: Tuple[Callable, Callable], scan_intervall: int) -> None:
        """Init and store callbacks."""
        self._callbacks: Dict[str, List[Callable]] = {}
        self._polling: bool = False
        self._update_all = api[0]
        self._is_alive = api[1]
        self.last_message_time: float = time.monotonic()
        self.scan_intervall = scan_intervall

    @property
    def alive(self) -> bool:
        """Return if the subscriptions are considered alive."""
        return (time.monotonic() - self.last_message_time) < self.scan_intervall

    def connection_lost(self) -> None:
        """Set the last message time to never."""
        self.last_message_time = -self.scan_intervall

    def subscribe(self, event_id: str, callback: Callable) -> None:
        """Subscribe to updates."""
        self._callbacks.setdefault(event_id, []).append(callback)
        if len(self._callbacks) == 1:
            self._polling = True
            asyncio.create_task(self._start())

    def unsubscribe(self, event_id: str, callback: Callable) -> None:
        """Unsubscribe from updates."""
        self._callbacks[event_id].remove(callback)
        if len(self._callbacks) == 0:
            self._stop()

    def notify(self, event_id: str) -> None:
        """Notify subscribers of an update."""
        self.last_message_time = time.monotonic()
        for callback in self._callbacks.get(event_id, []):
            callback()

    def _stop(self) -> None:
        """Stop polling."""
        self._polling = False
        self.connection_lost()

    async def _start(self) -> None:
        """Initialize polling."""
        while self._polling:
            if not await self._is_alive():
                self.connection_lost()
            else:
                await self._update_all()
            await asyncio.sleep(self.scan_intervall)
