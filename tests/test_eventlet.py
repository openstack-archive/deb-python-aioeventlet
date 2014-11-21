import eventlet
import tests

def slow_append(result, value, delay):
    eventlet.sleep(delay)
    result.append(value)
    return value * 10

def slow_error(delay):
    eventlet.sleep(delay)
    raise ValueError("error")

try:
    import asyncio

    exec('''if 1:
        @asyncio.coroutine
        def wait_greenthread(gt, loop=None):
            if loop is None:
                loop = asyncio.get_event_loop()
            fut = asyncio.Future(loop=loop)

            def copy_result(gt):
                try:
                    value = gt.wait()
                except Exception as exc:
                    loop.call_soon(fut.set_exception, exc)
                else:
                    loop.call_soon(fut.set_result, value)
            gt.link(copy_result)

            value = yield from fut
            return value

        @asyncio.coroutine
        def coro_chain_greenthread():
            result = []
            loop = asyncio.get_event_loop()

            g1 = eventlet.spawn(slow_append, result, 1, 0.2)

            value = yield from wait_greenthread(g1, loop=loop)
            result.append(value)

            g2 = eventlet.spawn(slow_append, result, 2, 0.1)
            value = yield from wait_greenthread(g2, loop=loop)
            result.append(value)

            g3 = eventlet.spawn(slow_error, 0.001)
            try:
                yield from wait_greenthread(g3, loop=loop)
            except ValueError as exc:
                result.append(str(exc))

            result.append(4)
            return result
    ''')
except ImportError:
    import trollius as asyncio
    from trollius import From, Return

    @asyncio.coroutine
    def wait_greenthread(gt, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        fut = asyncio.Future(loop=loop)

        def copy_result(gt):
            try:
                value = gt.wait()
            except Exception as exc:
                loop.call_soon(fut.set_exception, exc)
            else:
                loop.call_soon(fut.set_result, value)
        gt.link(copy_result)

        value = yield From(fut)
        raise Return(value)

    @asyncio.coroutine
    def coro_chain_greenthread():
        result = []
        loop = asyncio.get_event_loop()

        g1 = eventlet.spawn(slow_append, result, 1, 0.2)

        value = yield From(wait_greenthread(g1, loop=loop))
        result.append(value)

        g2 = eventlet.spawn(slow_append, result, 2, 0.1)
        value = yield From(wait_greenthread(g2, loop=loop))
        result.append(value)

        g3 = eventlet.spawn(slow_error, 0.001)
        try:
            yield From(wait_greenthread(g3, loop=loop))
        except ValueError as exc:
            result.append(str(exc))

        result.append(4)
        raise Return(result)


class EventletTests(tests.TestCase):
    def test_stop(self):
        def func():
            eventlet.spawn(self.loop.call_soon, self.loop.stop)

        def schedule_greenthread():
            eventlet.spawn(func)

        self.loop.call_soon(schedule_greenthread)
        self.loop.run_forever()

    def test_soon(self):
        result = []

        def func():
            result.append("spawn")
            self.loop.call_soon(self.loop.stop)

        def schedule_greenthread():
            eventlet.spawn(func)

        self.loop.call_soon(schedule_greenthread)
        self.loop.run_forever()
        self.assertEqual(result, ["spawn"])

    def test_soon_spawn(self):
        result = []

        def func1():
            result.append("spawn")

        def func2():
            result.append("spawn_after")
            self.loop.call_soon(self.loop.stop)

        def schedule_greenthread():
            eventlet.spawn(func1)
            eventlet.spawn_after(0.010, func2)

        self.loop.call_soon(schedule_greenthread)
        self.loop.run_forever()
        self.assertEqual(result, ["spawn", "spawn_after"])

    def test_coro_chain_greenthread(self):
        result = self.loop.run_until_complete(coro_chain_greenthread())
        self.assertEqual(result, [1, 10, 2, 20, 'error', 4])


if __name__ == '__main__':
    import unittest
    unittest.main()
