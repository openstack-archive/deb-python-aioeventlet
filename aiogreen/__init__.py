from eventlet import hubs
from trollius import futures
from trollius import selector_events
from trollius import selectors
from trollius import tasks
from trollius.base_events import BaseEventLoop
import errno
import eventlet.greenio
import eventlet.hubs.hub
import socket
import sys
import trollius
try:
    # Python 2
    import Queue as queue
except ImportError:
    import queue

threading = eventlet.patcher.original('threading')

_READ = eventlet.hubs.hub.READ
_WRITE = eventlet.hubs.hub.WRITE


def _is_main_thread():
    return isinstance(threading.current_thread(), threading._MainThread)


class EventLoopPolicy(trollius.AbstractEventLoopPolicy):
    def __init__(self):
        self._loop = None

    def get_event_loop(self):
        if not _is_main_thread():
            raise NotImplementedError("currently aiogreen can only run in the main thread")
        self._loop = EventLoop()
        return self._loop

    def new_event_loop(self):
        if self._loop is not None:
            raise NotImplementedError("cannot run two event loops in the same thread")
        return self.get_event_loop()

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


class TimerHandle(trollius.Handle):
    def __init__(self, callback, args, loop):
        super(TimerHandle, self).__init__(callback, args, loop)
        self._timer = None

    def _run(self):
        super(TimerHandle, self)._run()

    def cancel(self):
        super(TimerHandle, self).cancel()
        self._timer.cancel()


class SocketTransport(selector_events._SelectorSocketTransport):
    def __repr__(self):
        return '<%s fd=%s>' % (self.__class__.__name__, self._sock_fd)


class EventLoop(BaseEventLoop):
    def __init__(self):
        super(EventLoop, self).__init__()
        self._pool = eventlet.GreenPool()
        # Queue used by call_soon_threadsafe()
        self._queue = ThreadQueue(self)
        self._run = None
        if self.get_debug():
            hub = hubs.get_hub()
            hub.debug_blocking = True

    def time(self):
        # FIXME: is it safe to store the hub in an attribute of the event loop?
        # If yes, get the hub when the event loop is created
        hub = hubs.get_hub()
        return hub.clock()

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

    def call_later(self, delay, callback, *args):
        if 0:
            handle = TimerHandle(callback, args, self)

            # inline spawn_after() to get the timer object, to be able
            # to cancel directly the timer
            hub = hubs.get_hub()
            greenthread = eventlet.greenthread.GreenThread(hub.greenlet)
            timer = hub.schedule_call_global(delay, greenthread.switch,
                                             handle._run)

            handle._timer = timer
            return handle
        else:
            handle = trollius.Handle(callback, args, self)
            greenthread = eventlet.spawn_after(delay, self._call, handle)
            return handle

    def call_at(self, when, callback, *args):
        delay = when - self.time()
        return self.call_later(delay, callback, *args)

    # FIXME: run_in_executor(): use eventlet.tpool as the default executor?
    # It avoids the dependency to concurrent.futures, but later it would be
    # better to use concurrent.futures. So... What is the best?

    def stop(self):
        if self._run is None:
            # not running or stop already scheduled
            return
        self._run.send("stop")
        self._run = None

    def run_forever(self):
        if self._run is not None:
            raise RuntimeError("reentrant call to run_forever()")

        try:
            self._run = eventlet.event.Event()
            # use a local copy because stop() clears the attribute
            run = self._run
            run.wait()
        finally:
            self._run = None

    def close(self):
        super(EventLoop, self).close()
        self._queue.stop()

    def run_until_complete(self, future):
        # FIXME: don't copy/paste Trollius code, but
        # fix Trollius to call self.stop?
        self._check_closed()

        new_task = not isinstance(future, futures._FUTURE_CLASSES)
        future = tasks.async(future, loop=self)
        if new_task:
            # An exception is raised if the future didn't complete, so there
            # is no need to log the "destroy pending task" message
            future._log_destroy_pending = False

        def stop(fut):
            self.stop()

        future.add_done_callback(stop)
        self.run_forever()
        future.remove_done_callback(stop)
        if not future.done():
            raise RuntimeError('Event loop stopped before Future completed.')

        return future.result()

    def _throwback(self):
        # FIXME: do something?
        pass

    def _add_fd(self, event_type, fd, callback, args):
        hub = hubs.get_hub()
        fd = selectors._fileobj_to_fd(fd)
        def func(fd):
            return callback(*args)
        hub.add(event_type, fd, func, self._throwback, None)

    def add_reader(self, fd, callback, *args):
        self._add_fd(_READ, fd, callback, args)

    def add_writer(self, fd, callback, *args):
        self._add_fd(_WRITE, fd, callback, args)

    def _remove_fd(self, event_type, fd):
        hub = hubs.get_hub()
        fd = selectors._fileobj_to_fd(fd)
        try:
            listener = hub.listeners[event_type][fd]
        except KeyError:
            return False
        hub.remove(listener)
        return True

    def remove_reader(self, fd):
        return self._remove_fd(_READ, fd)

    def remove_writer(self, fd):
        return self._remove_fd(_WRITE, fd)

    def sock_connect(self, sock, address):
        # code adapted from GreenSocket.connect(),
        # the version without timeout
        fd = sock.fileno()
        while not eventlet.greenio.socket_connect(sock, address):
            try:
                hubs.trampoline(fd, write=True)
            except hubs.IOClosed:
                raise socket.error(errno.EBADFD)
            eventlet.greenio.socket_checkerr(sock)

    def _make_socket_transport(self, sock, protocol, waiter=None,
                               extra=None, server=None):
        return SocketTransport(self, sock, protocol, waiter, extra, server)
