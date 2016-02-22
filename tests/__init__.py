import aioeventlet
import sys
try:
    import asyncio
except ImportError:
    import trollius as asyncio
import unittest
try:
    from unittest import mock
except ImportError:
    import mock

class TestCase(unittest.TestCase):
    def setUp(self):
        policy = aioeventlet.EventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
        self.addCleanup(asyncio.set_event_loop_policy, None)

        self.loop = policy.get_event_loop()
        self.addCleanup(self.loop.close)
        self.addCleanup(asyncio.set_event_loop, None)

    if sys.version_info < (3,):
        def assertRaisesRegex(self, *args):
            return self.assertRaisesRegexp(*args)
