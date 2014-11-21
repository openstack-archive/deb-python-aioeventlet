Usage
=====

Use aiogreen with trollius
--------------------------

aiogreen can be used with trollius, coroutines written with ``yield
From(...)``. Using aiogreen with trollius is a good start to port project
written for eventlet to trollius.

To use aiogreen with trollius, set the event loop policy before using an event
loop, example::

    import aiogreen
    import trollius

    trollius.set_event_loop_policy(aiogreen.EventLoopPolicy())
    # ....

Hello World::

    import aiogreen
    import trollius as asyncio

    def hello_world():
        print("Hello World")
        loop.stop()

    asyncio.set_event_loop_policy(aiogreen.EventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.call_soon(hello_world)
    loop.run_forever()
    loop.close()

.. seealso::
   `Trollius documentation <http://trollius.readthedocs.org/>`_.


Use aiogreen with asyncio
-------------------------

aiogreen can be used with asyncio, coroutines written with ``yield from ...``.
To use aiogreen with asyncio, set the event loop policy before using an event
loop. Example::

    import aiogreen
    import asyncio

    asyncio.set_event_loop_policy(aiogreen.EventLoopPolicy())
    # ....

Setting the event loop policy should be enough to examples of the asyncio
documentation with the aiogreen event loop.

.. warning::
   Since aiogreen relies on eventlet, eventlet port to Python 3 is not complete
   and asyncio requires Python 3.3 or newer: using aiogreen with asyncio is not
   recommended yet. *Using aiogreen with trollius should be preferred right
   now*.  See the :ref:`status of the eventlet port to Python 3
   <eventlet-py3>`.

Hello World::

    import aiogreen
    import asyncio

    def hello_world():
        print("Hello World")
        loop.stop()

    asyncio.set_event_loop_policy(aiogreen.EventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.call_soon(hello_world)
    loop.run_forever()
    loop.close()

.. seealso::
   The `asyncio documentation
   <https://docs.python.org/dev/library/asyncio.html>`_.


API
===

aiogreen specific functions:

.. warning::
   aiogreen API is not stable yet. Function names may change in future
   releases, functions may change completly or even be removed.

.. function:: link_future(future)

   Wait for a future (or a task) from a greenthread.
   Return the result or raise the exception of the future.

   Example of greenthread waiting for a trollius task. The ``progress()``
   callback is called regulary to see that the event loop in not blocked::

        import aiogreen
        import eventlet
        import trollius as asyncio
        from trollius import From, Return

        def progress():
            print("computation in progress...")
            loop.call_later(0.5, progress)

        @asyncio.coroutine
        def coro_slow_sum(x, y):
            yield From(asyncio.sleep(1.0))
            raise Return(x + y)

        def green_sum():
            task = asyncio.async(coro_slow_sum(1, 2))

            loop.call_soon(progress)

            value = aiogreen.link_future(task)
            print("1 + 2 = %s" % value)
            loop.stop()

        asyncio.set_event_loop_policy(aiogreen.EventLoopPolicy())
        eventlet.spawn(green_sum)
        loop = asyncio.get_event_loop()
        loop.run_forever()
        loop.close()

   Output::

        computation in progress...
        computation in progress...
        computation in progress...
        1 + 2 = 3

.. function:: wrap_greenthread(gt)

   Wrap an eventlet GreenThread or a greenlet into a Future object.

   The Future object waits for the completion of a greenthread.

   The greenlet must not be running.

   In debug mode, if the greenthread raises an exception, the exception is
   logged to ``sys.stderr`` by eventlet, even if the exception is copied to the
   Future object.

   Example of trollius coroutine waiting for a greenthread. The ``progress()``
   callback is called regulary to see that the event loop in not blocked::

        import aiogreen
        import eventlet
        import trollius as asyncio
        from trollius import From, Return

        def progress():
            print("computation in progress...")
            loop.call_later(0.5, progress)

        def slow_sum(x, y):
            eventlet.sleep(1.0)
            return x + y

        @asyncio.coroutine
        def coro_sum():
            gt = eventlet.spawn(slow_sum, 1, 2)

            loop.call_soon(progress)

            fut = aiogreen.wrap_greenthread(gt, loop=loop)
            result = yield From(fut)
            print("1 + 2 = %s" % result)

        asyncio.set_event_loop_policy(aiogreen.EventLoopPolicy())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(coro_sum())
        loop.close()

   Output::

        computation in progress...
        computation in progress...
        computation in progress...
        1 + 2 = 3


Installation
============

Install aiogreen with pip
-------------------------

Type::

    pip install aiogreen

Install aiogreen on Windows with pip
------------------------------------

Procedure for Python 2.7:

* If pip is not installed yet, `install pip
  <http://www.pip-installer.org/en/latest/installing.html>`_: download
  ``get-pip.py`` and type::

  \Python27\python.exe get-pip.py

* Install aiogreen with pip::

  \Python27\python.exe -m pip install aiogreen

* pip also installs dependencies: ``eventlet`` and ``trollius``

Manual installation of aiogreen
-------------------------------

Requirements:

- eventlet 0.14 or newer
- asyncio or trollius:

  * Python 3.4 and newer: asyncio is now part of the stdlib (only eventlet is
    needed)
  * Python 3.3: need Tulip 0.4.1 or newer (``pip install asyncio``),
    but Tulip 3.4.1 or newer is recommended
  * Python 2.6-3.2: need Trollius 0.3 or newer (``pip install trollius``),
    but Trollius 1.0 or newer is recommended

Type::

    python setup.py install


Run tests
=========

Run tests with tox
------------------

The `tox project <https://testrun.org/tox/latest/>`_ can be used to build a
virtual environment with all runtime and test dependencies and run tests
against different Python versions (2.6, 2.7, 3.2, 3.3, 3.4).

To test all Python versions, just type::

    tox

To run tests with Python 2.7, type::

    tox -e py27

To run tests against other Python versions:

* ``py26``: Python 2.6
* ``py27``: Python 2.7
* ``py27_patch``: Python 2.7 with eventlet monkey patching
* ``py27_old``: Python 2.7 with the oldest supported versions of eventlet and
  trollius
* ``py32``: Python 3.2
* ``py33``: Python 3.3
* ``py33_old``: Python 3.3 with the oldest supported versions of eventlet and
  tulip
* ``py34``: Python 3.4

Run tests manually
------------------

Run the following command::

    python runtests.py -r
