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

eventlet 0.17 or newer is recommanded for Python 3 when monkey-patching is
enabled.
