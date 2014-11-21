import eventlet
import tests

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

            g1 = eventlet.spawn(eventlet_slow_append, result, 1, 0.2)

            value = yield from wait_greenthread(g1, loop=loop)
            result.append(value)

            g2 = eventlet.spawn(eventlet_slow_append, result, 2, 0.1)
            value = yield from wait_greenthread(g2, loop=loop)
            result.append(value)

            g3 = eventlet.spawn(eventlet_slow_error, 0.001)
            try:
                yield from wait_greenthread(g3, loop=loop)
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

        g1 = eventlet.spawn(eventlet_slow_append, result, 1, 0.2)

        value = yield From(wait_greenthread(g1, loop=loop))
        result.append(value)

        g2 = eventlet.spawn(eventlet_slow_append, result, 2, 0.1)
        value = yield From(wait_greenthread(g2, loop=loop))
        result.append(value)

        g3 = eventlet.spawn(eventlet_slow_error, 0.001)
        try:
            yield From(wait_greenthread(g3, loop=loop))
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


def wait_task(task):
    event = eventlet.event.Event()
    def done(fut):
        try:
            result = fut.result()
        except Exception as exc:
            # FIXME
            event.send_exception(exc)
        else:
            event.send(result)

    task.add_done_callback(done)
    return event.wait()

def greenthread_chain_coro(result, loop):
    t1 = loop.create_task(coro_slow_append(result, 1, 0.2))
    value = wait_task(t1)
    result.append(value)

    t2 = loop.create_task(coro_slow_append(result, 2, 0.1))
    value = wait_task(t2)
    result.append(value)

    t3 = loop.create_task(coro_slow_error(0.001))
    try:
        value = wait_task(t3)
    except ValueError as exc:
        result.append(str(exc))

    result.append(4)
    loop.call_soon(loop.stop)
    return result


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

    def test_greenthread_chain_coro(self):
        result = []
        self.loop.call_soon(eventlet.spawn, greenthread_chain_coro, result, self.loop)
        self.loop.run_forever()
        self.assertEqual(result, [1, 10, 2, 20, 'error', 4])


if __name__ == '__main__':
    import unittest
    unittest.main()
