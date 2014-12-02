import eventlet.hubs.hub
import greenlet
import logging
import signal
import sys
socket = eventlet.patcher.original('socket')
threading = eventlet.patcher.original('threading')

logger = logging.getLogger('aioeventlet')

try:
    import asyncio

    if sys.platform == 'win32':
        from asyncio.windows_utils import socketpair
    else:
        socketpair = socket.socketpair
except ImportError:
    import trollius as asyncio

    if sys.platform == 'win32':
        from trollius.windows_utils import socketpair
    else:
        socketpair = socket.socketpair

if eventlet.patcher.is_monkey_patched('socket'):
    # trollius must use call original socket and threading functions.
    # Examples: socket.socket(), socket.socketpair(),
    # threading.current_thread().
    asyncio.base_events.socket = socket
    asyncio.events.threading = threading
    if sys.platform == 'win32':
        asyncio.windows_events.socket = socket
        asyncio.windows_utils.socket = socket
    else:
        asyncio.unix_events.socket = socket
        asyncio.unix_events.threading = threading
    # FIXME: patch also trollius.py3_ssl

    # BaseDefaultEventLoopPolicy._Local must inherit from threading.local
    # of the original threading module, not the patched threading module
    class _Local(threading.local):
        _loop = None
        _set_called = False

    asyncio.events.BaseDefaultEventLoopPolicy._Local = _Local

_EVENT_READ = asyncio.selectors.EVENT_READ
_EVENT_WRITE = asyncio.selectors.EVENT_WRITE
_HUB_READ = eventlet.hubs.hub.READ
_HUB_WRITE = eventlet.hubs.hub.WRITE

# Eventlet 0.15 or newer?
_EVENTLET15 = hasattr(eventlet.hubs.hub.noop, 'mark_as_closed')


class _TpoolExecutor(object):
    def __init__(self, loop):
        import eventlet.tpool
        self._loop = loop
        self._tpool = eventlet.tpool

    def submit(self, fn, *args, **kwargs):
        f = asyncio.Future(loop=self._loop)
        try:
            res = self._tpool.execute(fn, *args, **kwargs)
        except Exception as exc:
            f.set_exception(exc)
        else:
            f.set_result(res)
        return f

    def shutdown(self, wait=True):
        self._tpool.killall()


class _Selector(asyncio.selectors._BaseSelectorImpl):
    def __init__(self, loop, hub):
        super(_Selector, self).__init__()
        # fd => events
        self._notified = {}
        self._loop = loop
        self._hub = hub
        # eventlet.event.Event() used by FD notifiers to wake up select()
        self._event = None

    def close(self):
        keys = list(self.get_map().values())
        for key in keys:
            self.unregister(key.fd)
        super(_Selector, self).close()

    def _add(self, fd, event):
        if event == _EVENT_READ:
            event_type = _HUB_READ
            func = self._notify_read
        else:
            event_type = _HUB_WRITE
            func = self._notify_write

        if _EVENTLET15:
            self._hub.add(event_type, fd, func, self._throwback, None)
        else:
            self._hub.add(event_type, fd, func)

    def register(self, fileobj, events, data=None):
        key = super(_Selector, self).register(fileobj, events, data)
        if events & _EVENT_READ:
            self._add(key.fd, _EVENT_READ)
        if events & _EVENT_WRITE:
            self._add(key.fd, _EVENT_WRITE)
        return key

    def _remove(self, fd, event):
        if event == _EVENT_READ:
            event_type = _HUB_READ
        else:
            event_type = _HUB_WRITE
        try:
            listener = self._hub.listeners[event_type][fd]
        except KeyError:
            pass
        else:
            self._hub.remove(listener)

    def unregister(self, fileobj):
        key = super(_Selector, self).unregister(fileobj)
        self._remove(key.fd, _EVENT_READ)
        self._remove(key.fd, _EVENT_WRITE)
        return key

    def _notify(self, fd, event):
        if fd in self._notified:
            self._notified[fd] |= event
        else:
            self._notified[fd] = event
        if self._event is not None and not self._event.ready():
            # wakeup the select() method
            self._event.send("ready")

    def _notify_read(self, fd):
        self._notify(fd, _EVENT_READ)

    def _notify_write(self, fd):
        self._notify(fd, _EVENT_WRITE)

    def _throwback(self, fd):
        # FIXME: do something with the FD in this case?
        pass

    def _read_events(self):
        notified = self._notified
        self._notified = {}
        ready = []
        for fd, events in notified.items():
            key = self.get_key(fd)
            ready.append((key, events & key.events))
        return ready

    def select(self, timeout):
        events = self._read_events()
        if events:
            return events

        self._event = eventlet.event.Event()
        try:
            if timeout is not None:
                def timeout_cb(event):
                    if event.ready():
                        return
                    event.send('timeout')

                eventlet.spawn_after(timeout, timeout_cb, self._event)

                self._event.wait()
                # FIXME: cancel the timeout_cb if wait() returns 'ready'?
            else:
                # blocking call
                self._event.wait()
            return self._read_events()
        finally:
            self._event = None


class EventLoop(asyncio.SelectorEventLoop):
    def __init__(self):
        self._greenthread = None

        # Store a reference to the hub to ensure
        # that we always use the same hub
        self._hub = eventlet.hubs.get_hub()

        selector = _Selector(self, self._hub)

        super(EventLoop, self).__init__(selector=selector)

        # Force a call to set_debug() to set hub.debug_blocking
        self.set_debug(self.get_debug())

        if eventlet.patcher.is_monkey_patched('thread'):
            self._default_executor = _TpoolExecutor(self)

    def call_soon(self, callback, *args):
        handle = super(EventLoop, self).call_soon(callback, *args)
        if self._selector is not None and self._selector._event:
            # selector.select() is running: write into the self-pipe to wake up
            # the selector
            self._write_to_self()
        return handle

    def call_at(self, when, callback, *args):
        handle = super(EventLoop, self).call_at(when, callback, *args)
        if self._selector is not None and self._selector._event:
            # selector.select() is running: write into the self-pipe to wake up
            # the selector
            self._write_to_self()
        return handle

    def set_debug(self, debug):
        super(EventLoop, self).set_debug(debug)

        self._hub.debug_exceptions = debug

        # Detect blocking eventlet functions. The feature is implemented with
        # signal.alarm() which is is not available on Windows. Signal handlers
        # can only be set from the main loop. So detecting blocking functions
        # cannot be used on Windows nor from a thread different than the main
        # thread.
        self._hub.debug_blocking = (
            debug
            and (sys.platform != 'win32')
            and isinstance(threading.current_thread(), threading._MainThread))

        if (self._hub.debug_blocking
        and hasattr(self, 'slow_callback_duration')):
            self._hub.debug_blocking_resolution = self.slow_callback_duration

    def run_forever(self):
        self._greenthread = eventlet.getcurrent()
        try:
            super(EventLoop, self).run_forever()
        finally:
            if self._hub.debug_blocking:
                # eventlet event loop is still running: cancel the current
                # detection of blocking tasks
                signal.alarm(0)
            self._greenthread = None

    def time(self):
        return self._hub.clock()


class EventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    _loop_factory = EventLoop


def wrap_greenthread(gt, loop=None):
    """Wrap an eventlet GreenThread, or a greenlet, into a Future object.

    The Future object waits for the completion of a greenthread. The result
    or the exception of the greenthread will be stored in the Future object.

    The greenthread must be wrapped before its execution starts. If the
    greenthread is running or already finished, an exception is raised.

    For greenlets, the run attribute must be set.
    """
    if loop is None:
        loop = asyncio.get_event_loop()
    fut = asyncio.Future(loop=loop)

    if not isinstance(gt, greenlet.greenlet):
        raise TypeError("greenthread or greenlet request, not %s"
                        % type(gt))

    if gt:
        raise RuntimeError("wrap_greenthread: the greenthread is running")
    if gt.dead:
        raise RuntimeError("wrap_greenthread: the greenthread already finished")

    if isinstance(gt, eventlet.greenthread.GreenThread):
        orig_main = gt.run
        def wrap_func(*args, **kw):
            try:
                orig_main(*args, **kw)
            except Exception as exc:
                fut.set_exception(exc)
            else:
                result = gt.wait()
                fut.set_result(result)
        gt.run = wrap_func
    else:
        try:
            orig_func = gt.run
        except AttributeError:
            raise RuntimeError("wrap_greenthread: the run attribute "
                               "of the greenlet is not set")
        def wrap_func(*args, **kw):
            try:
                result = orig_func(*args, **kw)
            except Exception as exc:
                fut.set_exception(exc)
            else:
                fut.set_result(result)
        gt.run = wrap_func
    return fut


def yield_future(future, loop=None):
    """Wait for a future, a task, or a coroutine object from a greenthread.

    Yield control other eligible eventlet coroutines until the future is done
    (finished successfully or failed with an exception).

    Return the result or raise the exception of the future.

    The function must not be called from the greenthread
    of the aioeventlet event loop.
    """
    future = asyncio.async(future, loop=loop)
    if future._loop._greenthread == eventlet.getcurrent():
        raise RuntimeError("yield_future() must not be called from "
                           "the greenthread of the aioeventlet event loop")

    event = eventlet.event.Event()
    def done(fut):
        try:
            result = fut.result()
        except Exception as exc:
            event.send_exception(exc)
        else:
            event.send(result)

    future.add_done_callback(done)
    return event.wait()
