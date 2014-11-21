Changelog
=========

Version 0.2 (development version)
---------------------------------

The core of the event loop was rewritten to fits better in asyncio and
eventlet. aiogreen now reuses more code from asyncio/trollius. The code
handling file descriptors was also fixed to respect asyncio contract:
only call the callback once per loop iteration.

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
