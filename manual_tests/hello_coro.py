#import logging; logging.basicConfig(level=logging.DEBUG)
import aiogreen
try:
    import asyncio

    exec('''if 1:
        def work():
            print("Hello")
            # retrieve the event loop from the policy
            yield from asyncio.sleep(1)
            print('World')
    ''')
except ImportError:
    import trollius as asyncio
    from trollius import From

    def work():
        print("Hello")
        # retrieve the event loop from the policy
        yield From(asyncio.sleep(1))
        print('World')

asyncio.set_event_loop_policy(aiogreen.EventLoopPolicy())
loop = asyncio.get_event_loop()
loop.run_until_complete(work())
loop.close()
