#!/usr/bin/env python3
"""Example code."""

import asyncio
import logging

import yaml

from truenaspy import TruenasClient, TruenasException

logger = logging.getLogger()
logger.setLevel(logging.INFO)
# create console handler and set level to debug
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

# Fill out the secrets in secrets.yaml, you can find an example
# _secrets.yaml file, which has to be renamed after filling out the secrets.
with open("./secrets.yaml", encoding="UTF-8") as file:
    secrets = yaml.safe_load(file)

TOKEN = secrets["TOKEN"]
HOST = secrets["HOST"]


async def async_main() -> None:
    """Main function."""
    try:
        api = TruenasClient(token=TOKEN, host=HOST, use_ssl=True, verify_ssl=False)
        rlst = await api.async_get_system()
        logger.info(rlst)

        # Fetch all data
        # await api.async_update()
        logger.info(await api.async_get_alerts())
        logger.info(await api.async_get_interfaces())
        logger.info(await api.async_get_datasets())
        logger.info(await api.async_get_pools())
        logger.info(await api.async_get_disks())
        logger.info(await api.async_get_jails())
        logger.info(await api.async_get_cloudsyncs())
        logger.info(await api.async_get_replications())
        logger.info(await api.async_get_snapshottasks())
        # logger.info(await api.async_get_charts())
        logger.info(await api.async_get_update())
        logger.info(await api.async_get_rsynctasks())
        logger.info(await api.async_get_docker())
        logger.info(await api.async_get_smartdisks())
        logger.info(await api.async_get_services())
        logger.info(await api.async_get_system())
        logger.info(await api.async_get_virtualmachines())
        logger.info(await api.async_get_apps())
        await api.async_close()

    except TruenasException as error:
        logger.error(error)

    # ==================
    # Subscribe at Event
    # ==================
    # api = TruenasClient(
    #     token=TOKEN, host=HOST, use_ssl=True, verify_ssl=False, scan_intervall=5
    # )

    # def log() -> None:
    #     logger.info("===== EVENT =====> Data: %s ", api.datasets)

    # api.subscribe(Events.DATASETS.value, log)

    # def log_disk() -> None:
    #     logger.info("===== EVENT =====> Disks: %s ", api.disks)

    # api.subscribe(Events.DISKS.value, log_disk)

    # polling = True
    # i = 0
    # while polling:
    #     i = i + 1
    #     await asyncio.sleep(15)
    #     if i == 5:
    #         api.unsubscribe(Events.DISKS.value, log_disk)
    #         polling = False

    # await api.async_close()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    asyncio.run(async_main())
