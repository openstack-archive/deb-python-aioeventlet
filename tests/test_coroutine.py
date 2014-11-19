import tests

try:
    import asyncio

    exec('''if 1:
        def hello_world(result, delay):
            result.append("Hello")
            # retrieve the event loop from the policy
            yield from asyncio.sleep(delay)
            result.append('World')
    ''')
except ImportError:
    import trollius as asyncio
    from trollius import From

    def hello_world(result, delay):
        result.append("Hello")
        # retrieve the event loop from the policy
        yield From(asyncio.sleep(delay))
        result.append('World')

class CallbackTests(tests.TestCase):
    def test_hello_world(self):
        result = []
        self.loop.run_until_complete(hello_world(result, 0.001))
        self.assertEqual(result, ['Hello', 'World'])
