import errno
import eventlet.hubs.hub
import functools
import sys
socket = eventlet.patcher.original('socket')
threading = eventlet.patcher.original('threading')

try:
    import asyncio
    from asyncio import base_events
    from asyncio import selector_events
    from asyncio import selectors
    from asyncio.log import logger

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


class _Selector(selectors._BaseSelectorImpl):
    def __init__(self, loop, hub):
        super(_Selector, self).__init__()
        self._notified = {
            _READ: set(),
            _WRITE: set(),
        }
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
        if event == selectors.EVENT_READ:
            event_type = _READ
            func = self._notify_read
        else:
            event_type = _WRITE
            func = self._notify_write

        if _EVENTLET15:
            self._hub.add(event_type, fd, func, self._throwback, None)
        else:
            self._hub.add(event_type, fd, func)

    def register(self, fileobj, events, data=None):
        key = super(_Selector, self).register(fileobj, events, data)
        if events & selectors.EVENT_READ:
            self._add(key.fd, selectors.EVENT_READ)
        if events & selectors.EVENT_WRITE:
            self._add(key.fd, selectors.EVENT_WRITE)
        return key

    def _remove(self, fd, event):
        if event == selectors.EVENT_READ:
            event_type = _READ
        else:
            event_type = _WRITE
        try:
            listener = self._hub.listeners[event_type][fd]
        except KeyError:
            return False
        self._hub.remove(listener)
        return True

    def unregister(self, fileobj):
        key = super(_Selector, self).unregister(fileobj)
        self._remove(key.fd, selectors.EVENT_READ)
        self._remove(key.fd, selectors.EVENT_WRITE)
        return key

    def _notify(self, event_type, fd):
        self._notified[event_type].add(fd)
        if self._event is not None and not self._event.ready():
            # wakeup the select() method
            self._event.send("ready")

    def _notify_read(self, fd):
        self._notify(_READ, fd)

    def _notify_write(self, fd):
        self._notify(_WRITE, fd)

    def _throwback(self, fd):
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
            for fd in notified[event_type]:
                key = self.get_key(fd)
                reader, writer = key.data
                if event_type == _READ:
                    ready.append((fd, reader))
                else:
                    ready.append((fd, writer))
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

        # Store a reference to the hub to ensure
        # that we always use the same hub
        self._hub = eventlet.hubs.get_hub()

        self._selector = _Selector(self, self._hub)

        # Force a call to set_debug() to set hub.debug_blocking
        self.set_debug(self.get_debug())

        self._ssock = None
        self._csock = None
        self._make_self_pipe()

        if eventlet.patcher.is_monkey_patched('thread'):
            self._default_executor = _TpoolExecutor(self)

    def set_debug(self, debug):
        super(EventLoop, self).set_debug(debug)

        # Detect blocking eventlet functions. The feature is implemented with
        # signal.alarm() which is is not available on Windows.
        self._hub.debug_blocking = debug and (sys.platform != 'win32')

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
        if self.is_closed():
            return
        self._close_self_pipe()
        super(EventLoop, self).close()
        self._selector.close()

    # FIXME: code adapted from trollius
    # ---

    # ---
    # FIXME: code copied from trollius (SelectorEventLoop)
    def add_reader(self, fd, callback, *args):
        """Add a reader callback."""
        self._check_closed()
        handle = asyncio.Handle(callback, args, self)
        try:
            key = self._selector.get_key(fd)
        except KeyError:
            self._selector.register(fd, selectors.EVENT_READ,
                                    (handle, None))
        else:
            mask, (reader, writer) = key.events, key.data
            self._selector.modify(fd, mask | selectors.EVENT_READ,
                                  (handle, writer))
            if reader is not None:
                reader.cancel()

    def add_writer(self, fd, callback, *args):
        """Add a writer callback.."""
        self._check_closed()
        handle = asyncio.Handle(callback, args, self)
        try:
            key = self._selector.get_key(fd)
        except KeyError:
            self._selector.register(fd, selectors.EVENT_WRITE,
                                    (None, handle))
        else:
            mask, (reader, writer) = key.events, key.data
            self._selector.modify(fd, mask | selectors.EVENT_WRITE,
                                  (reader, handle))
            if writer is not None:
                writer.cancel()

    def remove_reader(self, fd):
        if self.is_closed():
            return False
        try:
            key = self._selector.get_key(fd)
        except KeyError:
            return False
        else:
            mask, (reader, writer) = key.events, key.data
            mask &= ~selectors.EVENT_READ
            if not mask:
                self._selector.unregister(fd)
            else:
                self._selector.modify(fd, mask, (None, writer))

            if reader is not None:
                reader.cancel()
                return True
            else:
                return False

    def remove_writer(self, fd):
        if self.is_closed():
            return False
        try:
            key = self._selector.get_key(fd)
        except KeyError:
            return False
        else:
            mask, (reader, writer) = key.events, key.data
            # Remove both writer and connector.
            mask &= ~selectors.EVENT_WRITE
            if not mask:
                self._selector.unregister(fd)
            else:
                self._selector.modify(fd, mask, (reader, None))

            if writer is not None:
                writer.cancel()
                return True
            else:
                return False
    # FIXME: code copied from trollius (SelectorEventLoop)
    # ---

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
