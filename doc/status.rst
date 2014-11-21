Implemented
===========

Methods:

* call_at()
* call_later()
* call_soon()
* run_forever()
* run_in_executor()
* run_until_complete()
* create_connection(): TCP client
* stop()
* coroutines and tasks

aiogreen 0.1 was tested:

* on Python 2.7, 3.3 and 3.5
* on Linux and Windows
* with Trollius 1.0, 1.0.1 and 1.0.2
* with asyncio 0.4.1 and 3.4.2


To do (Not supported)
=====================

* wrap_greenthread() must not log the exception to sys.stderr if the
  greenthread didn't start
* run an event loop in a thread different than the main thread
* sockets: create_server, sock_recv
* pipes: connect_read_pipe
* subprocesses: need pipes
* signal handlers: add_signal_handler (only for pyevent hub?)
* tox.ini: test Python 3.3 with monkey-patching, see eventlet bug:
  https://github.com/eventlet/eventlet/pull/168


eventlet issues
===============

* eventlet monkey patching on Python 3 is incomplete. The most blocking issue
  is in the importlib: the thread module is patched to use greenthreads, but
  importlib really need to work on real threads. Pull request:
  https://github.com/eventlet/eventlet/pull/168
* eventlet.tpool.setup() seems to be broken on Windows in eventlet 0.15.
  Pull request:
  https://github.com/eventlet/eventlet/pull/167
* hub.debug_blocking is implemented with signal.alarm() which is is not
  available on Windows.


.. _eventlet-py3:

eventlet and Python 3
=====================

eventlet 0.15 is the first release supporting Python 3. Python 3 is only
supported if monkey-patching is not used.

Python 3 pull requests:

* Pull request #160: `Python 3 compat; Improve WSGI, WS, threading and tests
  <https://github.com/eventlet/eventlet/pull/160>`_ (sent the Nov 5, 2014): not
  merged yet
* Pull request #99, `Fix several issues with python3 thread patching
  <https://github.com/eventlet/eventlet/pull/99>`_ (sent the July 3, 2014): not
  merged yet, see the `commit
  <https://github.com/therve/eventlet/commit/9c3118162cf1ca1e50be330ba2a289f054c48d3c>`_

Python 3 issues:

* Issue #157: `eventlet hanging
  <https://github.com/eventlet/eventlet/issues/157>`_ (open since Oct 30, 2014)
* Issue #153: `py3: green.threading.local is not green
  <https://github.com/eventlet/eventlet/issues/153>`_ (closed the Nov 5, 2014)
* Issue #6: `Support Python 3.3
  <https://github.com/eventlet/eventlet/issues/6>`_ (open since Jan 2013)
