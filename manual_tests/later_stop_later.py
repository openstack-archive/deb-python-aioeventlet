import logging; logging.basicConfig(level=logging.DEBUG)
import aiogreen, trollius; trollius.set_event_loop_policy(aiogreen.EventLoopPolicy())
from trollius import From

import trollius
import eventlet
import time

def hello():
    print("Hello")

def world():
    print('World')
    loop.stop()

loop = trollius.get_event_loop()
loop.call_later(0.1, hello)
loop.call_later(0.2, loop.stop)
loop.call_later(0.3, world)
print("run forever")
loop.run_forever()

print("sleep")
eventlet.sleep(1.0)

print("run forever")
loop.run_forever()

loop.close()
