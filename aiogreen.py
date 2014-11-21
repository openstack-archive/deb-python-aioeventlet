import eventlet.hubs.hub
import sys
socket = eventlet.patcher.original('socket')
threading = eventlet.patcher.original('threading')

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


class SocketTransport(asyncio.selector_events._SelectorSocketTransport):
    def __repr__(self):
        # override repr because _SelectorSocketTransport depends on
        # loop._selector
        return '<%s fd=%s>' % (self.__class__.__name__, self._sock_fd)


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
        if self._selector._event:
            # selector.select() is running: use the thread-safe version to wake
            # up select().
            return self.call_soon_threadsafe(callback, *args)
        else:
            # Fast-path: no need to wake up th eevent loop.
            return super(EventLoop, self).call_soon(callback, *args)

    def call_at(self, when, callback, *args):
        if self._selector._event:
            # selector.select() is running: use the thread-safe version to wake
            # up select().
            return self.call_soon_threadsafe(super(EventLoop, self).call_at, when, callback, *args)
        else:
            # Fast-path: no need to wake up th eevent loop.
            return super(EventLoop, self).call_at(when, callback, *args)

    def set_debug(self, debug):
        super(EventLoop, self).set_debug(debug)

        self._hub.debug_exceptions = debug

        # Detect blocking eventlet functions. The feature is implemented with
        # signal.alarm() which is is not available on Windows.
        self._hub.debug_blocking = debug and (sys.platform != 'win32')

    def time(self):
        return self._hub.clock()


class EventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    _loop_factory = EventLoop


def wrap_greenthread(gt, loop=None):
    """Wrap an eventlet greenthread into a Future object."""
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
    return fut


def link_future(future):
    """Wait for a future.

    Wait for a future or a task from a greenthread.
    Return the result or raise the exception of the future.
    """
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
