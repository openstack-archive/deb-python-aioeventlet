import logging; logging.basicConfig(level=logging.DEBUG)
import aiogreen
import time
import trollius

def work():
    print("Hello")
    print("loop", trollius.get_event_loop())
    time.sleep(1)
    print('World')

trollius.set_event_loop_policy(aiogreen.EventLoopPolicy())
loop = trollius.get_event_loop()
loop.run_until_complete(loop.run_in_executor(None, work))
loop.run_until_complete(loop.run_in_executor(None, work))
loop.close()
