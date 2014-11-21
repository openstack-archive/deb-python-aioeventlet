import aiogreen
import eventlet
import tests
from tests import unittest


def eventlet_slow_append(result, value, delay):
    eventlet.sleep(delay)
    result.append(value)
    return value * 10

def eventlet_slow_error(delay):
    eventlet.sleep(delay)
    raise ValueError("error")

try:
    import asyncio

    exec('''if 1:
        @asyncio.coroutine
        def coro_wrap_greenthread():
            result = []
            loop = asyncio.get_event_loop()

            g1 = eventlet.spawn(eventlet_slow_append, result, 1, 0.2)

            fut = aiogreen.wrap_greenthread(g1, loop=loop)
            value = yield from fut
            result.append(value)

            g2 = eventlet.spawn(eventlet_slow_append, result, 2, 0.1)
            fut = aiogreen.wrap_greenthread(g2, loop=loop)
            value = yield from fut
            result.append(value)

            g3 = eventlet.spawn(eventlet_slow_error, 0.001)
            fut = aiogreen.wrap_greenthread(g3, loop=loop)
            try:
                yield from fut
            except ValueError as exc:
                result.append(str(exc))

            result.append(4)
            return result

        @asyncio.coroutine
        def coro_slow_append(result, value, delay):
            yield from asyncio.sleep(delay)
            result.append(value)
            return value * 10

        @asyncio.coroutine
        def coro_slow_error(delay):
            yield from asyncio.sleep(delay)
            raise ValueError("error")
    ''')
except ImportError:
    import trollius as asyncio
    from trollius import From, Return

    @asyncio.coroutine
    def coro_wrap_greenthread():
        result = []
        loop = asyncio.get_event_loop()

        g1 = eventlet.spawn(eventlet_slow_append, result, 1, 0.2)
        fut = aiogreen.wrap_greenthread(g1, loop=loop)
        value = yield From(fut)
        result.append(value)

        g2 = eventlet.spawn(eventlet_slow_append, result, 2, 0.1)
        fut = aiogreen.wrap_greenthread(g2, loop=loop)
        value = yield From(fut)
        result.append(value)

        g3 = eventlet.spawn(eventlet_slow_error, 0.001)
        fut = aiogreen.wrap_greenthread(g3, loop=loop)
        try:
            yield From(fut)
        except ValueError as exc:
            result.append(str(exc))

        result.append(4)
        raise Return(result)

    @asyncio.coroutine
    def coro_slow_append(result, value, delay):
        yield From(asyncio.sleep(delay))
        result.append(value)
        raise Return(value * 10)

    @asyncio.coroutine
    def coro_slow_error(delay):
        yield From(asyncio.sleep(delay))
        raise ValueError("error")


def greenthread_link_future(result, loop):
    try:
        t1 = asyncio.async(coro_slow_append(result, 1, 0.2), loop=loop)
        value = aiogreen.link_future(t1)
        result.append(value)

        t2 = asyncio.async(coro_slow_append(result, 2, 0.1), loop=loop)
        value = aiogreen.link_future(t2)
        result.append(value)

        t3 = asyncio.async(coro_slow_error(0.001), loop=loop)
        try:
            value = aiogreen.link_future(t3)
        except ValueError as exc:
            result.append(str(exc))

        result.append(4)
        return result
    except Exception as exc:
        result.append(repr(exc))
    finally:
        loop.call_soon(loop.stop)


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

    def test_greenthread_link_future(self):
        result = []
        self.loop.call_soon(eventlet.spawn,
                            greenthread_link_future, result, self.loop)
        self.loop.run_forever()
        self.assertEqual(result, [1, 10, 2, 20, 'error', 4])


class WrapGreenthreadTests(tests.TestCase):
    def test_wrap_greenthread(self):
        def func():
            eventlet.sleep(0.010)
            return 'ok'

        gt = eventlet.spawn(func)
        fut = aiogreen.wrap_greenthread(gt)
        result = self.loop.run_until_complete(fut)
        self.assertEqual(result, 'ok')

    def test_wrap_greenthread_running(self):
        event = eventlet.event.Event()

        def func():
            return aiogreen.wrap_greenthread(gt)

        self.loop.set_debug(False)
        gt = eventlet.spawn(func)
        fut1 = aiogreen.wrap_greenthread(gt)
        fut2 = self.loop.run_until_complete(fut1)
        fut3 = self.loop.run_until_complete(fut2)
        self.assertIs(fut3, fut2)

    @tests.mock.patch('aiogreen.logger')
    def test_wrap_greenthread_running_log(self, m_log):
        def func():
            return aiogreen.wrap_greenthread(gt)

        self.loop.set_debug(True)
        gt = eventlet.spawn(func)
        fut1 = aiogreen.wrap_greenthread(gt)
        fut2 = self.loop.run_until_complete(fut1)
        m_log.warning.assert_called_with("wrap_greenthread() called on "
                                         "a running greenthread")


    def test_wrap_greenthread_dead(self):
        def func():
            return 'ok'

        gt = eventlet.spawn(func)
        result = gt.wait()
        self.assertEqual(result, 'ok')

        fut = aiogreen.wrap_greenthread(gt)
        result = self.loop.run_until_complete(fut)
        self.assertEqual(result, 'ok')

    def test_coro_wrap_greenthread(self):
        result = self.loop.run_until_complete(coro_wrap_greenthread())
        self.assertEqual(result, [1, 10, 2, 20, 'error', 4])

    def test_wrap_invalid_type(self):
        def func():
            pass
        self.assertRaises(TypeError, aiogreen.wrap_greenthread, func)

        @asyncio.coroutine
        def coro_func():
            pass
        coro_obj = coro_func()
        self.addCleanup(coro_obj.close)
        self.assertRaises(TypeError, aiogreen.wrap_greenthread, coro_obj)


class WrapGreenletTests(tests.TestCase):
    def test_wrap_greenlet(self):
        def func():
            eventlet.sleep(0.010)
            return "ok"
        gt = eventlet.spawn_n(func)
        fut = aiogreen.wrap_greenthread(gt)
        result = self.loop.run_until_complete(fut)
        self.assertEqual(result, "ok")

    def test_wrap_greenlet_running(self):
        event = eventlet.event.Event()

        def func():
            try:
                gt = eventlet.getcurrent()
                fut = aiogreen.wrap_greenthread(gt)
            except Exception as exc:
                event.send_exception(exc)
            else:
                event.send(fut)

        gt = eventlet.spawn_n(func)
        self.assertRaises(RuntimeError, event.wait)

    def test_wrap_greenlet_dead(self):
        event = eventlet.event.Event()
        def func():
            event.send('done')
        gt = eventlet.spawn_n(func)
        event.wait()

        self.assertRaises(RuntimeError, aiogreen.wrap_greenthread, gt)


if __name__ == '__main__':
    import unittest
    unittest.main()
