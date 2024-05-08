#!/usr/bin/env python3
"""Example code."""

import asyncio
import logging

from truenaspy import Events, TruenasClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)
# create console handler and set level to debug
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

# Please , fill good values...
HOST = "my.nas.local:8080"
TOKEN = "xxxxxxxxxxxxxxxxxxxxxxxxx"


async def main() -> None:
    """Main function."""

    api = TruenasClient(token=TOKEN, host=HOST, use_ssl=True, verify_ssl=True)
    rlst = await api.async_get_system()
    logger.info(rlst)

    # Fetch all data
    await api.async_update()
    await api.async_get_interfaces()
    await api.async_get_services()
    await api.async_get_datasets()
    await api.async_get_pools()
    await api.async_get_disks()
    await api.async_get_jails()
    await api.async_get_virtualmachines()
    await api.async_get_cloudsync()
    await api.async_get_replications()
    await api.async_get_snapshottasks()
    await api.async_get_charts()
    await api.async_close()

    # ==================
    # Subscribe at Event
    # ==================
    api = TruenasClient(
        token=TOKEN, host=HOST, use_ssl=True, verify_ssl=False, scan_intervall=5
    )

    def log() -> None:
        logger.info("===== EVENT =====> Data: %s ", api.datasets)

    api.subscribe(Events.DATASETS.value, log)

    def log_disk() -> None:
        logger.info("===== EVENT =====> Disks: %s ", api.disks)

    api.subscribe(Events.DISKS.value, log_disk)

    polling = True
    i = 0
    while polling:
        i = i + 1
        await asyncio.sleep(15)
        if i == 5:
            api.unsubscribe(Events.DISKS.value, log_disk)
            polling = False

    await api.async_close()


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(main())
