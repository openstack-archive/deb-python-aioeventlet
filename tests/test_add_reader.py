from __future__ import absolute_import
from aiogreen import socketpair
import tests


class AddReaderTests(tests.TestCase):
    def test_add_reader(self):
        result = {'received': None}
        rsock, wsock = socketpair()
        self.addCleanup(rsock.close)
        self.addCleanup(wsock.close)

        def reader():
            data = rsock.recv(100)
            result['received'] = data
            self.loop.remove_reader(rsock)
            self.loop.stop()

        def writer():
            self.loop.remove_writer(wsock)
            self.loop.call_soon(wsock.send, b'abc')

        self.loop.add_reader(rsock, reader)
        self.loop.add_writer(wsock, writer)

        self.loop.run_forever()
        self.assertEqual(result['received'], b'abc')
