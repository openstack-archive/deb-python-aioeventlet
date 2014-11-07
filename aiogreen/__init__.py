import trollius
import eventlet

class EventLoopPolicy(trollius.DefaultEventLoopPolicy):
    pass

class EventLoop(trollius.SelectorEventLoop):
    def __init__(self, selector=None):
        super(EventLoop, self).__init__(selector=selector)
        self._pool = eventlet.GreenPool()
        self._timers = []

    def _call(self, handle):
        if handle._cancelled:
            return
        handle._run()

    def call_soon(self, callback, *args):
        handle = trollius.Handle(callback, args, self)
        self._pool.spawn(self._call, handle)
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

    def run_forever(self):
        self._pool.waitall()
        # FIXME: more efficient code :-)
        while self._timers:
            eventlet.sleep(0.1)
