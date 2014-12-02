import aioeventlet
import eventlet
import sys
import tests
from tests import unittest

SHORT_SLEEP = 0.001

def eventlet_slow_append(result, value, delay):
    eventlet.sleep(delay)
    result.append(value)
    return value * 10

def eventlet_slow_error():
    eventlet.sleep(SHORT_SLEEP)
    raise ValueError("error")

try:
    import asyncio

    exec('''if 1:
        @asyncio.coroutine
        def coro_wrap_greenthread():
            result = []

            gt = eventlet.spawn(eventlet_slow_append, result, 1, 0.020)
            value = yield from aioeventlet.wrap_greenthread(gt)
            result.append(value)

            gt = eventlet.spawn(eventlet_slow_append, result, 2, 0.010)
            value = yield from aioeventlet.wrap_greenthread(gt)
            result.append(value)

            gt = eventlet.spawn(eventlet_slow_error)
            try:
                yield from aioeventlet.wrap_greenthread(gt)
            except ValueError as exc:
                result.append(str(exc))

            result.append(4)
            return result

        @asyncio.coroutine
        def coro_slow_append(result, value, delay=SHORT_SLEEP):
            yield from asyncio.sleep(delay)
            result.append(value)
            return value * 10

        @asyncio.coroutine
        def coro_slow_error():
            yield from asyncio.sleep(0.001)
            raise ValueError("error")
    ''')
except ImportError:
    import trollius as asyncio
    from trollius import From, Return

    @asyncio.coroutine
    def coro_wrap_greenthread():
        result = []

        gt = eventlet.spawn(eventlet_slow_append, result, 1, 0.020)
        value = yield From(aioeventlet.wrap_greenthread(gt))
        result.append(value)

        gt = eventlet.spawn(eventlet_slow_append, result, 2, 0.010)
        value = yield From(aioeventlet.wrap_greenthread(gt))
        result.append(value)

        gt = eventlet.spawn(eventlet_slow_error)
        try:
            yield From(aioeventlet.wrap_greenthread(gt))
        except ValueError as exc:
            result.append(str(exc))

        result.append(4)
        raise Return(result)

    @asyncio.coroutine
    def coro_slow_append(result, value, delay=SHORT_SLEEP):
        yield From(asyncio.sleep(delay))
        result.append(value)
        raise Return(value * 10)

    @asyncio.coroutine
    def coro_slow_error():
        yield From(asyncio.sleep(0.001))
        raise ValueError("error")


def greenthread_yield_future(result, loop):
    try:
        value = aioeventlet.yield_future(coro_slow_append(result, 1, 0.020))
        result.append(value)

        value = aioeventlet.yield_future(coro_slow_append(result, 2, 0.010))
        result.append(value)

        try:
            value = aioeventlet.yield_future(coro_slow_error())
        except ValueError as exc:
            result.append(str(exc))

        result.append(4)
        return result
    except Exception as exc:
        result.append(repr(exc))
    finally:
        loop.stop()


class EventletTests(tests.TestCase):
    def test_stop(self):
        def func():
            self.loop.stop()

        eventlet.spawn(func)
        self.loop.run_forever()

    def test_soon(self):
        result = []

        def func():
            result.append("spawn")
            self.loop.stop()

        eventlet.spawn(func)
        self.loop.run_forever()
        self.assertEqual(result, ["spawn"])

    def test_soon_spawn(self):
        result = []

        def func1():
            result.append("spawn")

        def func2():
            result.append("spawn_after")
            self.loop.stop()

        def schedule_greenthread():
            eventlet.spawn(func1)
            eventlet.spawn_after(0.010, func2)

        self.loop.call_soon(schedule_greenthread)
        self.loop.run_forever()
        self.assertEqual(result, ["spawn", "spawn_after"])

    def test_set_debug(self):
        hub = eventlet.hubs.get_hub()
        self.assertIs(self.loop._hub, hub)

        self.loop.set_debug(False)
        self.assertEqual(hub.debug_exceptions, False)
        self.assertEqual(hub.debug_blocking, False)

        self.loop.set_debug(True)
        self.assertEqual(hub.debug_exceptions, True)
        if sys.platform != 'win32':
            self.assertEqual(hub.debug_blocking, True)
        else:
            self.assertEqual(hub.debug_blocking, False)


class LinkFutureTests(tests.TestCase):
    def test_greenthread_yield_future(self):
        result = []
        self.loop.call_soon(eventlet.spawn,
                            greenthread_yield_future, result, self.loop)
        self.loop.run_forever()
        self.assertEqual(result, [1, 10, 2, 20, 'error', 4])

    def test_link_coro(self):
        result = []

        def func(fut):
            value = aioeventlet.yield_future(coro_slow_append(result, 3))
            result.append(value)
            self.loop.stop()

        fut = asyncio.Future(loop=self.loop)
        eventlet.spawn(func, fut)
        self.loop.run_forever()
        self.assertEqual(result, [3, 30])

    def test_yield_future_not_running(self):
        result = []

        def func(event, fut):
            event.send('link')
            value = aioeventlet.yield_future(fut)
            result.append(value)
            self.loop.stop()

        event = eventlet.event.Event()
        fut = asyncio.Future(loop=self.loop)
        eventlet.spawn(func, event, fut)
        event.wait()

        self.loop.call_soon(fut.set_result, 21)
        self.loop.run_forever()
        self.assertEqual(result, [21])

    def test_yield_future_from_loop(self):
        result = []

        def func(fut):
            try:
                value = aioeventlet.yield_future(fut)
            except Exception as exc:
                result.append('error')
            else:
                result.append(value)
            self.loop.stop()

        fut = asyncio.Future(loop=self.loop)
        self.loop.call_soon(func, fut)
        self.loop.call_soon(fut.set_result, 'unused')
        self.loop.run_forever()
        self.assertEqual(result, ['error'])

    def test_yield_future_invalid_type(self):
        def func(obj):
            return aioeventlet.yield_future(obj)

        @asyncio.coroutine
        def coro_func():
            print("do something")

        def regular_func():
            return 3

        for obj in (coro_func, regular_func):
            gt = eventlet.spawn(func, coro_func)
            # ignore logged traceback
            with tests.mock.patch('traceback.print_exception') as m_print:
                self.assertRaises(TypeError, gt.wait)

    def test_yield_future_wrong_loop(self):
        result = []
        loop2 = asyncio.new_event_loop()
        self.addCleanup(loop2.close)

        def func(fut):
            try:
                value = aioeventlet.yield_future(fut, loop=loop2)
            except Exception as exc:
                result.append(str(exc))
            else:
                result.append(value)
            self.loop.stop()

        fut = asyncio.Future(loop=self.loop)
        self.loop.call_soon(func, fut)
        self.loop.call_soon(fut.set_result, 'unused')
        self.loop.run_forever()
        self.assertEqual(result[0],
                         'loop argument must agree with Future')


class WrapGreenthreadTests(tests.TestCase):
    def test_wrap_greenthread(self):
        def func():
            eventlet.sleep(0.010)
            return 'ok'

        gt = eventlet.spawn(func)
        fut = aioeventlet.wrap_greenthread(gt)
        result = self.loop.run_until_complete(fut)
        self.assertEqual(result, 'ok')

    def test_wrap_greenthread_exc(self):
        self.loop.set_debug(True)

        def func():
            raise ValueError(7)

        # FIXME: the unit test must fail!?
        with tests.mock.patch('traceback.print_exception') as print_exception:
            gt = eventlet.spawn(func)
            fut = aioeventlet.wrap_greenthread(gt)
            self.assertRaises(ValueError, self.loop.run_until_complete, fut)

        # the exception must not be logger by traceback: the caller must
        # consume the exception from the future object
        self.assertFalse(print_exception.called)

    def test_wrap_greenthread_running(self):
        def func():
            return aioeventlet.wrap_greenthread(gt)

        self.loop.set_debug(False)
        gt = eventlet.spawn(func)
        msg = "wrap_greenthread: the greenthread is running"
        self.assertRaisesRegexp(RuntimeError, msg, gt.wait)

    def test_wrap_greenthread_dead(self):
        def func():
            return 'ok'

        gt = eventlet.spawn(func)
        result = gt.wait()
        self.assertEqual(result, 'ok')

        msg = "wrap_greenthread: the greenthread already finished"
        self.assertRaisesRegexp(RuntimeError, msg,
                                aioeventlet.wrap_greenthread, gt)

    def test_coro_wrap_greenthread(self):
        result = self.loop.run_until_complete(coro_wrap_greenthread())
        self.assertEqual(result, [1, 10, 2, 20, 'error', 4])

    def test_wrap_invalid_type(self):
        def func():
            pass
        self.assertRaises(TypeError, aioeventlet.wrap_greenthread, func)

        @asyncio.coroutine
        def coro_func():
            pass
        coro_obj = coro_func()
        self.addCleanup(coro_obj.close)
        self.assertRaises(TypeError, aioeventlet.wrap_greenthread, coro_obj)


class WrapGreenletTests(tests.TestCase):
    def test_wrap_greenlet(self):
        def func():
            eventlet.sleep(0.010)
            return "ok"

        gt = eventlet.spawn_n(func)
        fut = aioeventlet.wrap_greenthread(gt)
        result = self.loop.run_until_complete(fut)
        self.assertEqual(result, "ok")

    def test_wrap_greenlet_exc(self):
        self.loop.set_debug(True)

        def func():
            raise ValueError(7)

        gt = eventlet.spawn_n(func)
        fut = aioeventlet.wrap_greenthread(gt)
        self.assertRaises(ValueError, self.loop.run_until_complete, fut)

    def test_wrap_greenlet_running(self):
        event = eventlet.event.Event()

        def func():
            try:
                gt = eventlet.getcurrent()
                fut = aioeventlet.wrap_greenthread(gt)
            except Exception as exc:
                event.send_exception(exc)
            else:
                event.send(fut)

        eventlet.spawn_n(func)
        msg = "wrap_greenthread: the greenthread is running"
        self.assertRaisesRegexp(RuntimeError, msg, event.wait)

    def test_wrap_greenlet_dead(self):
        event = eventlet.event.Event()
        def func():
            event.send('done')

        gt = eventlet.spawn_n(func)
        event.wait()
        msg = "wrap_greenthread: the greenthread already finished"
        self.assertRaisesRegexp(RuntimeError, msg, aioeventlet.wrap_greenthread, gt)


if __name__ == '__main__':
    import unittest
    unittest.main()
