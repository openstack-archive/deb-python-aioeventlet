aiogreen
========

.. image:: poplar_hawk-moth.jpg
   :alt: Poplar Hawk-moth (Laothoe populi), photo taken in France
   :align: right
   :target: https://www.flickr.com/photos/haypo/7181768969/in/set-72157629731066236

aiogreen implements the asyncio API (`PEP 3156
<http://www.python.org/dev/peps/pep-3156/>`_) on top of eventet. It makes
possible to write asyncio code in a project currently written for eventlet.

aiogreen allows to use greenthreads in asyncio coroutines, and to use asyncio
coroutines, tasks and futures in greenthreads: see :func:`link_future` and
:func:`wrap_greenthread` functions.

The main visible difference between trollius and aiogreen is that
``run_forever()``: ``run_forever()`` blocks with trollius, whereas it runs in a
greenthread with aiogreen. It means that it's possible to call
``run_forever()`` in the main thread and execute other greenthreads in
parallel.

* `aiogreen documentation <http://aiogreen.readthedocs.org/>`_
* `aiogreen project in the Python Cheeseshop (PyPI)
  <https://pypi.python.org/pypi/aiogreen>`_
* `aiogreen project at Bitbucket <https://bitbucket.org/haypo/aiogreen>`_
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

* `asyncio documentation <http://docs.python.org/dev/library/asyncio.html>`_
* `trollius documentation <http://trollius.readthedocs.org/>`_
* `tulip project <http://code.google.com/p/tulip/>`_
* `eventlet documentation <http://eventlet.net/doc/>`_
* `eventlet project <http://eventlet.net/>`_
* `greenlet documentation <http://greenlet.readthedocs.org/>`_

See also the `greenio project <https://github.com/1st1/greenio/>`_:
"Greenlets support for asyncio (PEP 3156)".
