#!/usr/bin/env python3
"""Example code."""

import asyncio
import logging
from typing import Any

import yaml

from truenaspy import Websocket, WebsocketError

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


async def job_handler(job_data: Any) -> None:
    """Handle job updates."""
    print("📢 Job update received:", job_data)


async def on_any_event(data: Any) -> None:
    """Handle any event."""
    print("🌐 Event:", data)


async def async_main() -> None:
    """Main function."""
    try:
        ws = Websocket(host=HOST, use_tls=True)
        await ws.async_connect()
        await ws.async_login(USERNAME, PASSWORD)

        info = await ws.async_send_msg(method="system.info")
        logger.info(info)
        info = await ws.async_send_msg(
            method="device.get_info", params={"type": "DISK"}
        )
        logger.info(info)
        info = await ws.async_send_msg(method="docker.status")
        logger.info(info)
        info = await ws.async_send_msg(method="docker.config")
        logger.info(info)
        info = await ws.async_send_msg(method="app.query")
        logger.info(info)
        info = await ws.async_send_msg(method="virt.global.config")
        logger.info(info)
        info = await ws.async_send_msg(method="pool.dataset.details")
        logger.info(info)
        info = await ws.async_send_msg(
            method="reporting.get_data",
            params=[[{"name": "cpu"}], {"unit": "HOUR"}],
        )
        logger.info(info)
        services = await ws.async_send_msg(method="service.query")
        logger.info(services)

        ## Subscribe at Event

        # Subsscribe events
        await ws.async_subscribe("core.get_jobs", job_handler)
        await ws.async_subscribe("alert.list", on_any_event)

        # Subsscribe all events
        await ws.async_subscribe("*", on_any_event)

        while ws.is_connected or ws.is_logged:
            await asyncio.sleep(1)

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
