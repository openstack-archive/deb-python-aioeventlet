import logging; logging.basicConfig(level=logging.DEBUG)
import aiogreen
import time
try:
    import asyncio
except ImportError:
    import trollius as asyncio

def work():
    print("Hello")
    print("loop", asyncio.get_event_loop())
    time.sleep(1)
    print('World')

asyncio.set_event_loop_policy(aiogreen.EventLoopPolicy())
loop = asyncio.get_event_loop()
loop.run_until_complete(loop.run_in_executor(None, work))
loop.run_until_complete(loop.run_in_executor(None, work))
loop.close()
