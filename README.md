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
from truenaspy import TrueNASAPI

TOKEN="012345"
HOST="1.2.3.4:8080"

async def main():
    api = TrueNASAPI(token=TOKEN, host=HOST, use_ssl=False, verify_ssl=False)
    rslt = await api.async_get_system()
    print(rlst)
    await api.async_close()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
```

Have a look at the [example.py](https://github.com/cyr-ius/truenaspy/blob/master/example.py) for a more complete overview.
