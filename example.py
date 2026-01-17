#!/usr/bin/env python3
"""Example code."""

import asyncio
import logging
from typing import Any

import yaml

from truenaspy import TruenasWebsocket, WebsocketError

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

HOST = secrets["HOST"]
USERNAME = secrets["USERNAME"]
PASSWORD = secrets["PASSWORD"]


async def async_main() -> None:
    """Main function."""

    ws = TruenasWebsocket(host=HOST, use_tls=True, verify_ssl=False)

    try:
        # -----------------------------------
        # Connect to websocket
        # -----------------------------------

        listener = await ws.async_connect(USERNAME, PASSWORD)

        # -----------------------------------
        # Execute a command
        # -----------------------------------

        info = await ws.async_call(method="system.info")
        logger.info(info)
        info = await ws.async_call(
            method="device.get_info",
            params={"type": "DISK", "get_partitions": True, "serials_only": False},
        )
        logger.info(info)
        info = await ws.async_call(method="disk.query")
        logger.info(info)
        info = await ws.async_call(method="device.get_info", params={"type": "GPU"})
        logger.info(info)
        info = await ws.async_call(method="docker.status")
        logger.info(info)
        info = await ws.async_call(method="docker.config")
        logger.info(info)
        info = await ws.async_call(method="app.query")
        logger.info(info)
        info = await ws.async_call(method="virt.instance.query")
        logger.info(info)
        info = await ws.async_call(method="pool.query")
        logger.info(info)
        info = await ws.async_call(method="pool.dataset.details")
        logger.info(info)
        for dataset in info:
            info = await ws.async_call(
                method="pool.dataset.snapshot_count", params=[dataset["id"]]
            )
            logger.info("%s - %s", dataset["id"], info)

        info = await ws.async_call(method="service.query")
        logger.info(info)
        info = await ws.async_call(method="reporting.netdata_graphs")
        logger.info(info)
        info = await ws.async_call(
            method="reporting.netdata_graph", params=["disktemp"]
        )
        logger.info(info)

        # info = await ws.async_call(method="disk.temperatures")
        # logger.info(info)
        info = await ws.async_call(method="disk.details")
        logger.info(info)
        # info = await ws.async_call(method="update.available_versions")
        # logger.info(info)
        info = await ws.async_call(method="disk.get_used")
        logger.info(info)
        info = await ws.async_call(method="alert.list")
        logger.info(info)

        # -----------------------------------
        # Example complex query
        # -----------------------------------

        # info = await ws.async_call(
        #     method="reporting.netdata_get_data",
        #     params=[
        #         [
        #             {"name": "cpu"},
        #             {"name": "cputemp"},
        #             # {"name": "disk"},
        #             # {"name": "disktemp"},
        #         ],
        #         {"unit": "DAY", "aggregate": True},
        #     ],
        # )
        # logger.info(info)
        #
        # info = await ws.async_call(
        #     method="reporting.get_data",
        #     params=[[{"name": "cpu"}], {"unit": "HOUR"}],
        # )
        # logger.info(info)
        #
        # info = await ws.async_call(
        #     method="zfs.snapshot.query",
        #     # params=[[], {"count": True}],
        #     params=[
        #         [["pool", "!=", "boot-pool"], ["pool", "!=", "freenas-boot"]],
        #         {"select": ["dataset", "snapshot_name", "pool"]},
        #     ],
        # )
        # logger.info(info)

        # -----------------------------------
        #  Subscribe Event
        # -----------------------------------

        async def on_any_event(data: Any) -> None:
            """Handle any event."""
            logger.info("🌐 Collection: %s, Event: %s", data["collection"], data)

        await ws.async_subscribe("reporting.realtime", on_any_event)
        # await ws.async_subscribe("reporting.processes", on_any_event)
        # await ws.async_subscribe("system.health", on_any_event)
        # await ws.async_subscribe("trueview.stats", on_any_event)
        # await ws.async_unsubscribe("reporting.realtime")

        # -----------------------------------
        # Subsscribe all events
        # -----------------------------------

        # await ws.async_subscribe("*", on_any_event)
        # await ws.async_unsubscribe("*")

        # -----------------------------------
        # Execute a command
        # -----------------------------------

        # try:
        #     job = await ws.async_call("service.stop", params=["snmp"])
        #     print("Job:", job)
        # except WebsocketError as error:
        #     logger.error(f"Error: {error}")

        await listener

    except TimeoutError:
        logger.error("Timeout error")
    except WebsocketError as error:
        logger.error(f"Websocket error: {error}")
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt")
    except Exception as error:
        logger.error(error)
    finally:
        await ws.async_close()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    asyncio.run(async_main())
