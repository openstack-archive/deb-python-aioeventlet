import logging; logging.basicConfig(level=logging.DEBUG)
import aiogreen, trollius; trollius.set_event_loop_policy(aiogreen.EventLoopPolicy())
from trollius import From

import trollius
import time

def hello():
    print("Hello")

def stop():
    print("stop")
    loop.stop()

def world():
    print('World')
    print("stop")
    loop.stop()

loop = trollius.get_event_loop()
loop.call_soon(hello)
loop.call_soon(stop)
loop.call_soon(world)
print("run forever")
loop.run_forever()

print("sleep")
time.sleep(1.0)

print("run forever")
loop.run_forever()

loop.close()
