import sys
import errno
import eventlet.greenio
import eventlet.semaphore
import eventlet.hubs.hub
import functools
import heapq
socket = eventlet.patcher.original('socket')
threading = eventlet.patcher.original('threading')
try:
    # Python 2
    import Queue as queue
except ImportError:
    import queue
try:
    import asyncio
    from asyncio import base_events
    from asyncio import selector_events
    from asyncio import selectors
    from asyncio.log import logger

    _FUTURE_CLASSES = (asyncio.Future,)

    if sys.platform == 'win32':
        from asyncio.windows_utils import socketpair
    else:
        socketpair = socket.socketpair
except ImportError:
    import trollius as asyncio
    from trollius import base_events
    from trollius import selector_events
    from trollius import selectors
    from trollius.log import logger

    if hasattr(asyncio.tasks, '_FUTURE_CLASSES'):
        # Trollius 1.0.0
        _FUTURE_CLASSES = asyncio.tasks._FUTURE_CLASSES
    else:
        # Trollius >= 1.0.1
        _FUTURE_CLASSES = asyncio.futures._FUTURE_CLASSES

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

_READ = eventlet.hubs.hub.READ
_WRITE = eventlet.hubs.hub.WRITE

# Eventlet 0.15 or newer?
_EVENTLET15 = hasattr(eventlet.hubs.hub.noop, 'mark_as_closed')

# Error numbers catched by Python 3.3 BlockingIOError exception
_BLOCKING_IO_ERRNOS = set((
    errno.EAGAIN,
    errno.EALREADY,
    errno.EINPROGRESS,
    errno.EWOULDBLOCK,
))


def _is_main_thread():
    return isinstance(threading.current_thread(), threading._MainThread)


class SocketTransport(selector_events._SelectorSocketTransport):
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


class _Selector(object):
    def __init__(self, loop):
        self._notified = {
            _READ: set(),
            _WRITE: set(),
        }
        self._listeners = {
            _READ: {},
            _WRITE: {},
        }
        self._event = None
        self._loop = loop

    def register(self, event_type, fd, handle):
        # FIXME: support multiple callbacks for fd
        self._listeners[event_type][fd] = handle

    def unregister(self, event_type, fd):
        try:
            handle = self._listeners[event_type].pop(fd)
        except KeyError:
            return False
        else:
            handle.cancel()
            return True

    def _notify(self, event_type, fd):
        self._notified[event_type].add(fd)
        if self._event is not None and not self._event.ready():
            # wakeup the select() method
            self._event.send("ready")

    def notify_read(self, fd):
        self._notify(_READ, fd)

    def notify_write(self, fd):
        self._notify(_WRITE, fd)

    def throwback(self, fd):
        # FIXME: do something with the FD in this case?
        pass

    def _read_events(self):
        notified = self._notified
        self._notified = {
            _READ: set(),
            _WRITE: set(),
        }
        ready = []
        for event_type in (_READ, _WRITE):
            listeners = self._listeners[event_type]
            for fd in notified[event_type]:
                handle = listeners[fd]
                ready.append((fd, handle))
        return ready

    def select(self, timeout):
        events = self._read_events()
        if events:
            return events

        self._event = eventlet.event.Event()
        try:
            if timeout is not None:
                # FIXME: don't use polling
                endtime = self._loop.time() + timeout
                while self._loop.time() <= endtime:
                    if self._event.ready():
                        break
                    eventlet.sleep(0.010)
            else:
                # blocking call
                self._event.wait()
            return self._read_events()
        finally:
            self._event = None


class EventLoop(base_events.BaseEventLoop):
    def __init__(self):
        super(EventLoop, self).__init__()
        self._selector = _Selector(self)

        # Store a reference to the hub to ensure
        # that we always use the same hub
        self._hub = eventlet.hubs.get_hub()
        if self.get_debug():
            self._hub.debug_blocking = True

        self._ssock = None
        self._csock = None
        self._make_self_pipe()

        if eventlet.patcher.is_monkey_patched('thread'):
            self._default_executor = _TpoolExecutor(self)

    def time(self):
        return self._hub.clock()

    def _process_events(self, events):
        for fd, handle in events:
            self._ready.append(handle)

    # ---
    # FIXME: code adapted from trollius
    def _make_self_pipe(self):
        assert self._ssock is None
        self._ssock, self._csock = socketpair()
        self._ssock.setblocking(False)
        self._csock.setblocking(False)
        self.add_reader(self._ssock.fileno(), self._read_from_self)

    def _close_self_pipe(self):
        assert self._ssock is not None
        self.remove_reader(self._ssock.fileno())
        self._ssock.close()
        self._ssock = None
        self._csock.close()
        self._csock = None

    def _read_from_self(self):
        while True:
            try:
                data = self._ssock.recv(4096)
                if not data:
                    break
            except socket.error as exc:
                if exc.errno in _BLOCKING_IO_ERRNOS:
                    break
                elif exc.errno == errno.EINTR:
                    continue
                else:
                    raise

    def _write_to_self(self):
        # This may be called from a different thread, possibly after
        # _close_self_pipe() has been called or even while it is
        # running.  Guard for self._csock being None or closed.  When
        # a socket is closed, send() raises OSError (with errno set to
        # EBADF, but let's not rely on the exact error code).
        csock = self._csock
        if csock is not None:
            try:
                csock.send(b'\0')
            except socket.error:
                if self.get_debug():
                    logger.debug("Fail to write a null byte into the "
                                 "self-pipe socket",
                                 exc_info=True)
    def close(self):
        super(EventLoop, self).close()
        self._close_self_pipe()

    # FIXME: code adapted from trollius
    # ---

    def _add_fd(self, event_type, fd, callback, args):
        fd = selectors._fileobj_to_fd(fd)
        handle = asyncio.Handle(callback, args, self)

        if event_type == _READ:
            func = self._selector.notify_read
        else:
            func = self._selector.notify_write

        self._selector.register(event_type, fd, handle)
        try:
            if _EVENTLET15:
                throwback = self._selector.throwback
                self._hub.add(event_type, fd, func, throwback, None)
            else:
                self._hub.add(event_type, fd, func)
        except:
            self._selector.unregister(event_type, fd)
            raise

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
        self._selector.unregister(event_type, fd)
        return True

    def remove_reader(self, fd):
        return self._remove_fd(_READ, fd)

    def remove_writer(self, fd):
        return self._remove_fd(_WRITE, fd)

    # ----
    # FIXME: reuse SelectorEventLoop.sock_connect() code instead of
    # copy/paste the code. Code adapted to work on Python 2 and Python 3,
    # and work on asyncio and trollius
    def sock_connect(self, sock, address):
        """Connect to a remote socket at address.

        The address must be already resolved to avoid the trap of hanging the
        entire event loop when the address requires doing a DNS lookup. For
        example, it must be an IP address, not an hostname, for AF_INET and
        AF_INET6 address families. Use getaddrinfo() to resolve the hostname
        asynchronously.

        This method is a coroutine.
        """
        if self.get_debug() and sock.gettimeout() != 0:
            raise ValueError("the socket must be non-blocking")
        fut = asyncio.Future(loop=self)
        try:
            base_events._check_resolved_address(sock, address)
        except ValueError as err:
            fut.set_exception(err)
        else:
            self._sock_connect(fut, sock, address)
        return fut

    def _sock_connect(self, fut, sock, address):
        fd = sock.fileno()
        try:
            while True:
                try:
                    sock.connect(address)
                except OSError as exc:
                    if exc.errno == errno.EINTR:
                        continue
                    else:
                        raise
                else:
                    break
        except socket.error as exc:
            if exc.errno in _BLOCKING_IO_ERRNOS:
                cb = functools.partial(self._sock_connect_done, sock)
                fut.add_done_callback(cb)
                self.add_writer(fd, self._sock_connect_cb, fut, sock, address)
            else:
                raise
        except Exception as exc:
            fut.set_exception(exc)
        else:
            fut.set_result(None)

    def _sock_connect_done(self, sock, fut):
        self.remove_writer(sock.fileno())

    def _sock_connect_cb(self, fut, sock, address):
        if fut.cancelled():
            return

        try:
            err = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            if err != 0:
                # Jump to the except clause below.
                raise OSError(err, 'Connect call failed %s' % (address,))
        except socket.error as exc:
            if exc.errno in _BLOCKING_IO_ERRNOS or exc.errno == errno.EINTR:
                # socket is still registered, the callback will
                # be retried later
                pass
            else:
                raise
        except Exception as exc:
            fut.set_exception(exc)
        else:
            fut.set_result(None)
    # FIXME: reuse SelectorEventLoop.sock_connect() code instead of
    # copy/paste the code
    # ----

    def _make_socket_transport(self, sock, protocol, waiter=None,
                               extra=None, server=None):
        return SocketTransport(self, sock, protocol, waiter, extra, server)


class EventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    _loop_factory = EventLoop
