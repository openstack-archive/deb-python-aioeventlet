import aiogreen
import unittest

class TestCase(unittest.TestCase):
    def setUp(self):
        self.loop = aiogreen.EventLoop()
        self.addCleanup(self.loop.close)
