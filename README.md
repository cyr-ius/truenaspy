# Truenaspy

Fetch data from TrueNas

## Install

Use the PIP package manager

```bash
$ pip install truenaspy
```

Or manually download and install the last version from github

```bash
$ git clone https://github.com/cyr-ius/truenaspy.git
$ python setup.py install
```

## Get started

```python
# Import the truenaspy package.
from truenaspy import TruenasWebsocket

HOST="1.2.3.4:8080"

async def main():
    websocket = TruenasWebsocket(host=HOST, use_tls=True, verify_ssl=False)
    listener = await websocket.async_connect(USERNAME, PASSWORD)
    info = await ws.async_call(method="system.info")
    print(rlst)
    await websocket.async_close()

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
asyncio.run(async_main())
```

Have a look at the [example.py](https://github.com/cyr-ius/truenaspy/blob/master/example.py) for a more complete overview.
