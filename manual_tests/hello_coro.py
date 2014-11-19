import logging; logging.basicConfig(level=logging.DEBUG)
import aiogreen, trollius; trollius.set_event_loop_policy(aiogreen.EventLoopPolicy())
from trollius import From

import trollius as asyncio

def work():
    print("Hello")
    yield From(trollius.sleep(1))
    print('World')

loop = asyncio.get_event_loop()
loop.run_until_complete(work())
loop.close()
