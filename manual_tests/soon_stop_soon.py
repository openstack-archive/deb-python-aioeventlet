import aiogreen
import eventlet
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

loop = aiogreen.EventLoop()
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
