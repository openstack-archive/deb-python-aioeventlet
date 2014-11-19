import sys
try:
    import asyncio
    from asyncio import selector_events
    from asyncio import selectors
    from asyncio.base_events import BaseEventLoop
    if sys.platform == 'win32':
        from asyncio.windows_utils import socketpair
    else:
        from socket import socketpair

    _FUTURE_CLASSES = (asyncio.Future,)
except ImportError:
    import trollius as asyncio
    from trollius import selector_events
    from trollius import selectors
    from trollius.base_events import BaseEventLoop

    if hasattr(asyncio.tasks, '_FUTURE_CLASSES'):
        # Trollius 1.0.0
        _FUTURE_CLASSES = asyncio.tasks._FUTURE_CLASSES
    else:
        # Trollius 1.0.1 and newer
        _FUTURE_CLASSES = asyncio.futures._FUTURE_CLASSES
    if sys.platform == 'win32':
        from trollius.windows_utils import socketpair
    else:
        from socket import socketpair
import errno
import eventlet.greenio
import eventlet.semaphore
import eventlet.hubs.hub
import heapq
import socket
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


class EventLoopPolicy(asyncio.AbstractEventLoopPolicy):
    def __init__(self):
        self._loop = None

    def get_event_loop(self):
        if not _is_main_thread():
            return None
        if self._loop is None:
            self._loop = EventLoop()
        return self._loop

    def new_event_loop(self):
        return EventLoop()

    def set_event_loop(self, loop):
        if not _is_main_thread():
            raise NotImplementedError("aiogreen can only run in the main thread")
        self._loop = loop


class _ThreadQueue:
    """Queue used by EventLoop.call_soon_threadsafe().

    Store handles in a queue and schedule them in the thread of the event
    loop as soon as possible.
    """
    def __init__(self, loop):
        self._loop = loop
        self._queue = queue.Queue()
        self._ssock = None
        self._csock = None

    def _consume(self):
        # schedule callbacks queued by put()
        while True:
            try:
                handle = self._queue.get(block=False)
            except eventlet.queue.Empty:
                break
            self._loop._call_soon_handle(handle)

        # flush data of the self-pipe
        while True:
            try:
                data = self._ssock.recv(4096)
                if not data:
                    break
            except socket.error:
                break

    def start(self):
        assert self._ssock is None
        self._ssock, self._csock = socketpair()
        self._ssock.setblocking(False)
        self._csock.setblocking(False)
        self._loop.add_reader(self._ssock.fileno(), self._consume)

    def put(self, handle):
        self._queue.put(handle)
        # use a local variable to be greenthread-safe
        csock = self._csock
        if csock is not None:
            csock.send(b'\0')

    def stop(self):
        if self._ssock is None:
            return
        self._loop.remove_reader(self._ssock.fileno())
        self._ssock.close()
        self._ssock = None
        self._csock.close()
        self._csock = None


class SocketTransport(selector_events._SelectorSocketTransport):
    def __repr__(self):
        # override repr because _SelectorSocketTransport depends on
        # loop._selector
        return '<%s fd=%s>' % (self.__class__.__name__, self._sock_fd)


def noop(*args, **kw):
    pass


class _Scheduler(object):
    """Schedule a call to loop._run_once().

    - schedule() calls loop._run_once() as soon as possible.
      If schedule_at() was called, replace this previous scheduled call.
    - schedule_at(when) calls it at the requested timestamp.
      If schedule() was called, do nothing.
    - stop() cancels the scheduled call.

    The scheduler is protected by an eventlet semaphore.
    """

    def __init__(self, loop):
        self._loop = loop
        self._greenthread = None
        self._timer = None
        self._lock = eventlet.semaphore.Semaphore()

    def schedule(self):
        with self._lock:
            self._schedule_unlocked()

    def _schedule_unlocked(self):
        if self._greenthread is not None:
            # already scheduled
            return

        # the greenthread will be called before the next timer,
        # cancel the timer if any
        self._unschedule_timer_unlocked()

        # it's safe to call spawn_n() with the lock:
        # it doesn't call _run_once() immediatly
        self._greenthread = eventlet.spawn_n(self._loop._run_once)

    def _unschedule_unlocked(self):
        if (self._greenthread is not None
        # If the greenthread is running, there is not need to cancel it.
        # Only cancel the greenthread if it didn't start yet.
        and not self._greenthread
        and not self._greenthread.dead):
            self._greenthread.run = noop
        self._greenthread = None

    def schedule_timer(self, when):
        with self._lock:
            if self._greenthread is not None:
                # already scheduled
                return

            delay = when - self._loop.time()
            if delay <= 0:
                self._schedule_unlocked()
                return

            if self._timer is not None:
                if self._timer[0] <= when:
                    # the existing timer will be triggered earlier,
                    # nothing to do
                    return

                # the existing timer was scheduled later, replace it
                self._timer[1].cancel()
                self._timer = None

            hub = self._loop._hub
            greenthread = eventlet.greenthread.GreenThread(hub.greenlet)
            # it is safe to call schedule_call_global() with the lock:
            # it does not switch to _run_once() immediatly (it creates a timer
            # and adds it a the "next timers").
            greentimer = hub.schedule_call_global(delay,
                                                  greenthread.switch,
                                                  self._loop._run_once, (), {})
            self._timer = (when, greentimer)

    def _unschedule_timer_unlocked(self):
        if self._timer is None:
            return

        when, greentimer = self._timer
        self._timer = None
        greentimer.cancel()

    def stop(self):
        with self._lock:
            self._unschedule_unlocked()
            self._unschedule_timer_unlocked()


class EventLoop(BaseEventLoop):
    def __init__(self):
        super(EventLoop, self).__init__()

        # Store a reference to the hub to ensure
        # that we always use the same hub
        self._hub = eventlet.hubs.get_hub()
        if self.get_debug():
            self._hub.debug_blocking = True

        # Queue used by call_soon_threadsafe()
        self._thread_queue = _ThreadQueue(self)

        # Event used to stop the event loop and to check if the event loop is
        # running?
        self._stop_event = None

        # Scheduler used to schedule a call to the loop._run_once() method
        self._scheduler = _Scheduler(self)

    def time(self):
        return self._hub.clock()

    def _call(self, handle):
        if handle._cancelled:
            return
        handle._run()

    def _call_soon_handle(self, handle):
        self._ready.append(handle)
        self._scheduler.schedule()

    def is_running(self):
        return (self._stop_event is not None)

    def _run_once(self):
        assert self.is_running()

        # FIXME: copy optimization from asyncio to remove cancelled timers

        # Handle 'later' callbacks that are ready.
        end_time = self.time() + self._clock_resolution
        while self._scheduled:
            handle = self._scheduled[0]
            if handle._when >= end_time:
                break
            handle = heapq.heappop(self._scheduled)
            handle._scheduled = False
            if handle._cancelled:
                continue
            self._ready.append(handle)

        # use a local copy because stop() clears the attribute
        stop_event = self._stop_event

        ntodo = len(self._ready)
        for i in range(ntodo):
            if stop_event.ready():
                # stop() has been called
                break
            handle = self._ready.popleft()
            if handle._cancelled:
                continue
            handle._run()

        self._scheduler.stop()
        self._reschedule()

    def _reschedule(self):
        if self._ready:
            self._scheduler.schedule()
        elif self._scheduled:
            handle = self._scheduled[0]
            self._scheduler.schedule_timer(handle._when)

    def call_soon(self, callback, *args):
        handle = asyncio.Handle(callback, args, self)
        self._call_soon_handle(handle)
        return handle

    def call_soon_threadsafe(self, callback, *args):
        handle = asyncio.Handle(callback, args, self)
        self._thread_queue.put(handle)
        return handle

    def call_at(self, when, callback, *args):
        timer = asyncio.TimerHandle(when, callback, args, self)
        heapq.heappush(self._scheduled, timer)
        self._scheduler.schedule_timer(when)
        return timer

    def call_later(self, delay, callback, *args):
        when = self.time() + delay
        return self.call_at(when, callback, *args)

    def _timer_handle_cancelled(self, handle):
        super(EventLoop, self)._timer_handle_cancelled(handle)
        # FIXME: optimization, reschedule _run_once() if the cancelled timer
        # was the next timer

    def stop(self):
        if self._stop_event is None:
            # not running or stop already scheduled
            return
        self._stop_event.send("stop")
        self._stop_event = None

    def run_forever(self):
        if self._stop_event is not None:
            raise RuntimeError("reentrant call to run_forever()")

        # Start to thread queue in run_forever() to create a greenthread linked
        # to the current greenthread
        self._thread_queue.start()
        self._reschedule()
        try:
            self._stop_event = eventlet.event.Event()
            # use a local copy because stop() clears the attribute
            stop_event = self._stop_event
            stop_event.wait()
        finally:
            self._stop_event = None
            self._scheduler.stop()
            # Stop the greenthread of the thread queue.
            # call_soon_threadsafe() can still be called, handles will be
            # stored in the thread queue.
            self._thread_queue.stop()

    def close(self):
        super(EventLoop, self).close()

    def run_until_complete(self, future):
        # FIXME: don't copy/paste Trollius code, but
        # fix Trollius to call self.stop?
        self._check_closed()

        new_task = not isinstance(future, _FUTURE_CLASSES)
        future = asyncio.async(future, loop=self)
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
        # FIXME: do something with the FD in this case?
        pass

    def _add_fd(self, event_type, fd, callback, args):
        fd = selectors._fileobj_to_fd(fd)
        def func(fd):
            return callback(*args)
        self._hub.add(event_type, fd, func, self._throwback, None)

    def add_reader(self, fd, callback, *args):
        self._add_fd(_READ, fd, callback, args)

    def add_writer(self, fd, callback, *args):
        self._add_fd(_WRITE, fd, callback, args)

    def _remove_fd(self, event_type, fd):
        fd = selectors._fileobj_to_fd(fd)
        try:
            listener = self._hub.listeners[event_type][fd]
        except KeyError:
            return False
        self._hub.remove(listener)
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
                eventlet.hubs.trampoline(fd, write=True)
            except eventlet.hubs.IOClosed:
                raise socket.error(errno.EBADFD)
            eventlet.greenio.socket_checkerr(sock)

    def _make_socket_transport(self, sock, protocol, waiter=None,
                               extra=None, server=None):
        return SocketTransport(self, sock, protocol, waiter, extra, server)
