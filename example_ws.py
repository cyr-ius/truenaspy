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
    try:
        ws = TruenasWebsocket(host=HOST, use_tls=True, verify_ssl=False)
        listener = await ws.async_connect(USERNAME, PASSWORD)

        info = await ws.async_call(method="system.info")
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

        ## Complex query

        # info = await ws.async_call(
        #     method="reporting.get_data",
        #     params=[[{"name": "cpu"}], {"unit": "HOUR"}],
        # )
        # logger.info(info)
        # info = await ws.async_call(
        #     method="zfs.snapshot.query",
        #     # params=[[], {"count": True}],
        #     params=[
        #         [["pool", "!=", "boot-pool"], ["pool", "!=", "freenas-boot"]],
        #         {"select": ["dataset", "snapshot_name", "pool"]},
        #     ],
        # )
        # logger.info(info)

        ## Subscribe at Event

        # events = {}
        # async def on_job_handler(data) -> None:
        #     """Calbback for websocket."""
        #     name = data["collection"].replace(".", "_")
        #     if events.get(name) is None:
        #         events[name] = []
        #     if data["msg"].upper() == "ADDED":
        #         events[name].append(data["fields"])
        #     if data["msg"].upper() == "REMOVED":
        #         id_to_remove = data["id"]
        #         events[name] = [
        #             event for event in events[name] if event["id"] != id_to_remove
        #         ]
        #     print("📢 Job list:", events)
        # await ws.async_subscribe("core.get_jobs", on_job_handler)

        async def on_any_event(data: Any) -> None:
            """Handle any event."""
            print("🌐 Event:", data)

        await ws.async_subscribe("reporting.realtime", on_any_event)
        # await ws.async_unsubscribe("reporting.realtime")

        # Subsscribe all events

        # await ws.async_subscribe("*", on_any_event)
        # await ws.async_unsubscribe("*")

        ## Execute a command

        # try:
        #     job = await ws.async_call("service.stop", params=["snmp"])
        #     print("Job:", job)
        # except WebsocketError as error:
        #     logger.error(f"Error: {error}")

        await listener

    except asyncio.TimeoutError:
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
