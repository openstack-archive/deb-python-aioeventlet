import trollius
from trollius.base_events import BaseEventLoop
import eventlet
import sys
try:
    # Python 2
    import Queue as queue
except ImportError:
    import queue

if sys.version_info < (3,):
    threading = eventlet.patcher.original('threading')
    _get_thread_ident = threading._get_ident
    # FIXME: get the main thread on Python 2
    _main_thread_id = _get_thread_ident()
else:
    # Python 3
    threading = eventlet.patcher.original('threading')
    _get_thread_ident = threading.get_ident
    _main_thread_id = threading.main_thread().ident

def _is_main_thread():
    return _get_thread_ident() == _main_thread_id

class EventLoopPolicy(trollius.AbstractEventLoopPolicy):
    def __init__(self):
        self._loop = None

    def new_event_loop(self):
        if not _is_main_thread():
            raise NotImplementedError("currently aiogreen can only run in the main thread")
        if self._loop is not None:
            raise NotImplementedError("cannot run two event loops in the same thread")
        self._loop = EventLoop()
        return self._loop

    def get_event_loop(self):
        return self.new_event_loop()

    def set_event_loop(self, loop):
        if self._loop is not None:
            raise NotImplementedError("cannot run two event loops in the same thread")
        self._loop = loop


# FIXME: is there a more efficient way to exchange data between two threads?
class ThreadQueue:
    def __init__(self, loop):
        self._loop = loop
        self._queue = queue.Queue()
        # FIXME: only schedule the consumer at the first call
        # to consume?
        self._greenthread = eventlet.spawn(self._consume)

    def _consume(self):
        while True:
            try:
                # FIXME: don't use polling
                stop, handle = self._queue.get(timeout=0.01)
            except eventlet.queue.Empty:
                eventlet.sleep(0)
                continue

            if stop:
                break
            self._loop._call_soon_handle(handle)

    def put(self, item):
        self._queue.put((False, item))

    def stop(self):
        self._queue.put((True, None))
        self._greenthread.wait()


class EventLoop(BaseEventLoop):
    def __init__(self):
        super(EventLoop, self).__init__()
        self._pool = eventlet.GreenPool()
        self._timers = []
        self._in_executor = []
        # Queue used by call_soon_threadsafe()
        self._queue = ThreadQueue(self)

    def _call(self, handle):
        if handle._cancelled:
            return
        handle._run()

    def _call_soon_handle(self, handle):
        self._pool.spawn(self._call, handle)

    def call_soon(self, callback, *args):
        handle = trollius.Handle(callback, args, self)
        self._call_soon_handle(handle)
        return handle

    def call_soon_threadsafe(self, callback, *args):
        handle = trollius.Handle(callback, args, self)
        self._queue.put(handle)
        return handle

    def _call_later(self, handle):
        greenthread = eventlet.getcurrent()
        self._timers.remove(greenthread)
        self._call(handle)

    def call_later(self, delay, callback, *args):
        # FIXME: cancelling the handle should unschedule the timer
        handle = trollius.Handle(callback, args, self)
        greenthread = eventlet.spawn_after(delay, self._call_later, handle)
        self._timers.append(greenthread)
        return handle

    def call_at(self, when, callback, *args):
        delay = when - self.time()
        return self.call_later(delay, callback, *args)

    def run_in_executor(self, executor, callback, *args):
        # FIXME: use eventlet.tpool as the default executor?
        fut = super(EventLoop, self).run_in_executor(executor, callback, *args)
        if not fut.done():
            self._in_executor.append(fut)
        return fut

    def run_forever(self):
        # FIXME: don't use polling
        while True:
            self._in_executor = [fut for fut in self._in_executor
                                 if not fut.done()]
            if not self._timers and not self._in_executor:
                return
            eventlet.sleep(1.0)
        self._pool.waitall()

    def close(self):
        super(EventLoop, self).close()
        self._queue.stop()

    def _not_implemented(self):
        raise NotImplementedError("method not supported in aiogreen yet")

    def stop(self):
        self._not_implemented()

    def run_until_complete(self, future):
        self._not_implemented()
