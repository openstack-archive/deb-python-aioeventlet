To do
=====

* support monkey-patching enabled after loading the aioeventlet module
* register signals in eventlet hub, only needed for pyevent hub?
* port greenio examples to aioeventlet
* write unit tests for, and maybe also examples for:

  - TCP server
  - UDP socket
  - UNIX socket
  - pipes
  - signals
  - subprocesses

* experiment running an event loop in a thread different than the main thread


.. _eventlet-py3:

eventlet and Python 3
=====================

eventlet 0.16 or newer is recommanded for Python 3 when monkey-patching is
enabled.

eventlet 0.15 is the first release supporting Python 3, its monkey-patching
does not work with Python 3.

Python 3 pull requests:

* `Fix threading.Condition with monkey-patching on Python 3.3 and newer #187
  <https://github.com/eventlet/eventlet/pull/187>`_
* `Fix monkey-patched os.open(): add dir_fd parameter #170
  <https://github.com/eventlet/eventlet/pull/170>`_, merged!
* `Fix monkey_patch() on Python 3 #168
  <https://github.com/eventlet/eventlet/pull/168>`_, merged!
* `Python 3 compat; Improve WSGI, WS, threading and tests #160
  <https://github.com/eventlet/eventlet/pull/160>`_ (sent the Nov 5, 2014):
  merged!
* `Fix several issues with python3 thread patching #99
  <https://github.com/eventlet/eventlet/pull/99>`_ (sent the July 3, 2014): not
  merged but it is not more needed (issues fixed by other changes), see the
  `commit
  <https://github.com/therve/eventlet/commit/9c3118162cf1ca1e50be330ba2a289f054c48d3c>`_

Python 3 issues:

* Issue #157: `eventlet hanging
  <https://github.com/eventlet/eventlet/issues/157>`_ (open since Oct 30, 2014)
* Issue #153: `py3: green.threading.local is not green
  <https://github.com/eventlet/eventlet/issues/153>`_ (closed the Nov 5, 2014)
* Issue #6: `Support Python 3.3
  <https://github.com/eventlet/eventlet/issues/6>`_ (open since Jan 2013)
