aioeventlet
===========

.. image:: poplar_hawk-moth.jpg
   :alt: Poplar Hawk-moth (Laothoe populi), photo taken in France
   :align: right
   :target: https://www.flickr.com/photos/haypo/7181768969/in/set-72157629731066236

aioeventlet implements the asyncio API (`PEP 3156
<http://www.python.org/dev/peps/pep-3156/>`_) on top of eventlet. It makes
possible to write asyncio code in a project currently written for eventlet.

aioeventlet allows to use greenthreads in asyncio coroutines, and to use asyncio
coroutines, tasks and futures in greenthreads: see :func:`yield_future` and
:func:`wrap_greenthread` functions.

The main visible difference between aioeventlet and trollius is the behaviour of
``run_forever()``: ``run_forever()`` blocks with trollius, whereas it runs in a
greenthread with aioeventlet. It means that aioeventlet event loop can run in an
greenthread while the Python main thread runs other greenthreads in parallel.

* `aioeventlet documentation <http://aioeventlet.readthedocs.org/>`_
* `aioeventlet project in the Python Cheeseshop (PyPI)
  <https://pypi.python.org/pypi/aioeventlet>`_
* `aioeventlet project at Bitbucket <https://bitbucket.org/haypo/aioeventlet>`_
* Copyright/license: Open source, Apache 2.0. Enjoy!

Table Of Contents
=================

.. toctree::

   using
   status
   openstack
   changelog

Event loops
===========

Projects used by aioeventlet:

* `asyncio documentation <http://docs.python.org/dev/library/asyncio.html>`_
* `trollius documentation <http://trollius.readthedocs.org/>`_
* `tulip project <http://code.google.com/p/tulip/>`_
* `eventlet documentation <http://eventlet.net/doc/>`_
* `eventlet project <http://eventlet.net/>`_
* `greenlet documentation <http://greenlet.readthedocs.org/>`_

See also:

* `aiogevent <https://pypi.python.org/pypi/aiogevent>`_: asyncio API
  implemented on top of gevent
* `geventreactor <https://pypi.python.org/pypi/geventreactor>`_: gevent-powered
  Twisted reactor
* `greenio <https://github.com/1st1/greenio/>`_: Greenlets support
  for asyncio (PEP 3156)
* `tulipcore <https://github.com/decentfox/tulipcore>`_: run gevent code on
  top of asyncio
