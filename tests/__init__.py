import aiogreen
import unittest
try:
    import asyncio
except ImportError:
    import trollius as asyncio

class TestCase(unittest.TestCase):
    def setUp(self):
        policy = aiogreen.EventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
        self.addCleanup(asyncio.set_event_loop_policy, None)

        self.loop = policy.get_event_loop()
        self.addCleanup(self.loop.close)
        self.addCleanup(asyncio.set_event_loop, None)
