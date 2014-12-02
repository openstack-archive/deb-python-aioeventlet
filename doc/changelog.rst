Changelog
=========

2014-12-03: Version 0.4
-----------------------

* Rename the project from ``aiogreen`` to ``aioeventlet``
* Rename the ``link_future()`` function to :func:`yield_future`

2014-11-23: version 0.3
-----------------------

* :func:`wrap_greenthread` now raises an exception if the greenthread is
  running or already finished. In debug mode, the exception is not more logged
  to sys.stderr for greenthreads.
* :func:`link_future` now accepts coroutine objects.
* :func:`link_future` now raises an exception if it is called from the
  greenthread of the aiogreen event loop.
* Fix eventlet detection of blocking tasks: cancel the alarm when the aiogreen
  event loop stops.
* Fix to run an event loop in a thread different than the main thread in debug
  mode: disable eventlet "debug_blocking", it is implemented with the SIGALRM
  signal, but signal handlers can only be set in the main thread.

2014-11-21: version 0.2
-----------------------

aiogreen event loop has been rewritten to reuse more asyncio/trollius code. It
now only has a few specific code.

It is now possible use greenthreads in asyncio coroutines, and to use asyncio
coroutines, tasks and futures in greenthreads: see :func:`link_future` and
:func:`wrap_greenthread` functions.

All asyncio network are supported: TCP, UCP and UNIX clients and servers.

Support of pipes, signal handlers and subprocess is still experimental.

Changes:

* Add a Sphinx documentation published at http://aiogreen.readthedocs.org/
* Add the :func:`link_future` function: wait for a future from a
  greenthread.
* Add the :func:`wrap_greenthread` function: wrap a greenthread into a Future
* Support also eventlet 0.14, not only eventlet 0.15 or newer
* Support eventlet with monkey-patching
* Rewrite the code handling file descriptors to ensure that the listener is
  only called once per loop iteration, to respect asyncio specification.
* Simplify the loop iteration: remove custom code to reuse instead the
  asyncio/trollius code (_run_once)
* Reuse call_soon, call_soon_threadsafe, call_at, call_later from
  asyncio/trollius, remove custom code
* sock_connect() is now asynchronous
* Add a suite of automated unit tests
* Fix EventLoop.stop(): don't stop immediatly, but schedule stopping the event
  loop with call_soon()
* Add tox.ini to run tests with tox
* Setting debug mode of the event loop doesn't enable "debug_blocking" of
  eventlet on Windows anymore, the feature is not implemented on Windows
  in eventlet.
* add_reader() and add_writer() now cancels the previous handle and sets
  a new handle
* In debug mode, detect calls to call_soon() from greenthreads which are not
  threadsafe (would not wake up the event loop).
* Only set "debug_exceptions" of the eventlet hub when the debug mode of the
  event loop is enabled.

2014-11-19: version 0.1
-----------------------

* First public release
