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

Tests of aiogreen 0.1:

* Tested on Python 2.7, 3.3 and 3.5
* Tested on Linux and Windows
* Tested with Trollius 1.0, 1.0.1 and 1.0.2
* Tested with asyncio 0.4.1 and 3.4.2


To do (Not supported)
=====================

* run an event loop in a thread different than the main thread
* sockets: create_server, sock_recv
* pipes: connect_read_pipe
* subprocesses: need pipes
* signal handlers: add_signal_handler (only for pyevent hub?)
* tox.ini: add py33_patch. eventlet with Python 3 and monkey-patch causes
  an issue in importlib.


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


eventlet and Python 3
=====================

Issues:

* https://github.com/eventlet/eventlet/issues/6 (root py3 issue)
* https://github.com/eventlet/eventlet/issues/157 (py3 related?)
* https://github.com/eventlet/eventlet/issues/153 (py3 related?)

Pull requests:

* https://github.com/eventlet/eventlet/pull/99 : complete monkey-patching
* => commit: https://github.com/therve/eventlet/commit/9c3118162cf1ca1e50be330ba2a289f054c48d3c
* https://github.com/eventlet/eventlet/pull/160 (py3 related?)

OpenStack Kilo Summit:

* https://etherpad.openstack.org/p/kilo-oslo-python-3
* https://etherpad.openstack.org/p/kilo-oslo-oslo.messaging
* https://etherpad.openstack.org/p/py34-transition (tangentially related)
