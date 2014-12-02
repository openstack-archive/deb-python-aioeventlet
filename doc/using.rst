Usage
=====

Use aioeventlet with trollius
-----------------------------

aioeventlet can be used with trollius, coroutines written with ``yield
From(...)``. Using aioeventlet with trollius is a good start to port project
written for eventlet to trollius.

To use aioeventlet with trollius, set the event loop policy before using an event
loop, example::

    import aioeventlet
    import trollius

    trollius.set_event_loop_policy(aioeventlet.EventLoopPolicy())
    # ....

Hello World::

    import aioeventlet
    import trollius as asyncio

    def hello_world():
        print("Hello World")
        loop.stop()

    asyncio.set_event_loop_policy(aioeventlet.EventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.call_soon(hello_world)
    loop.run_forever()
    loop.close()

.. seealso::
   `Trollius documentation <http://trollius.readthedocs.org/>`_.


Use aioeventlet with asyncio
----------------------------

aioeventlet can be used with asyncio, coroutines written with ``yield from ...``.
To use aioeventlet with asyncio, set the event loop policy before using an event
loop. Example::

    import aioeventlet
    import asyncio

    asyncio.set_event_loop_policy(aioeventlet.EventLoopPolicy())
    # ....

Setting the event loop policy should be enough to examples of the asyncio
documentation with the aioeventlet event loop.

.. warning::
   Since aioeventlet relies on eventlet, eventlet port to Python 3 is not complete
   and asyncio requires Python 3.3 or newer: using aioeventlet with asyncio is not
   recommended yet. *Using aioeventlet with trollius should be preferred right
   now*.  See the :ref:`status of the eventlet port to Python 3
   <eventlet-py3>`.

Hello World::

    import aioeventlet
    import asyncio

    def hello_world():
        print("Hello World")
        loop.stop()

    asyncio.set_event_loop_policy(aioeventlet.EventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.call_soon(hello_world)
    loop.run_forever()
    loop.close()

.. seealso::
   The `asyncio documentation
   <https://docs.python.org/dev/library/asyncio.html>`_.


Threads
-------

Running an event loop in a thread different than the main thread is currently
experimental.

An eventlet Event object is not thread-safe, it must only be used in the
same thread. Use threading.Event to signal events between threads,
and threading.Queue to pass data between threads.

Use ``threading = eventlet.patcher.original('threading')`` to get the original
threading instead of ``import threading``.

It is not possible to run two aioeventlet event loops in the same thread.


Debug mode
----------

To enable the debug mode globally when using trollius, set the environment
variable ``TROLLIUSDEBUG`` to ``1``. To see debug traces, set the log level of
the trollius logger to ``logging.DEBUG``.  The simplest configuration is::

   import logging
   # ...
   logging.basicConfig(level=logging.DEBUG)

If you use asyncio,  use the ``PYTHONASYNCIODEBUG`` environment variable
instead of the ``TROLLIUSDEBUG`` variable.

You can also call ``loop.set_debug(True)`` to enable the debug mode of the
event loop, but it enables less debug checks.

.. seealso::
   Read the `Develop with asyncio
   <https://docs.python.org/dev/library/asyncio-dev.html>`_ section of the
   asyncio documentation.


API
===

aioeventlet specific functions:

.. warning::
   aioeventlet API is not considered as stable yet.

yield_future
------------

.. function:: yield_future(future, loop=None)

   Wait for a future, a task, or a coroutine object from a greenthread.

   Return the result or raise the exception of the future.

   The function must not be called from the greenthread of the aioeventlet event
   loop.

   .. versionchanged:: 0.4

      Rename the function from ``wrap_future()`` to :func:`yield_future`.

   .. versionchanged:: 0.3

      Coroutine objects are also accepted. Added the *loop* parameter.
      An exception is raised if it is called from the greenthread of the
      aioeventlet event loop.

   Example of greenthread waiting for a trollius task. The ``progress()``
   callback is called regulary to see that the event loop in not blocked::

        import aioeventlet
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
            loop.call_soon(progress)

            task = asyncio.async(coro_slow_sum(1, 2))

            value = aioeventlet.yield_future(task)
            print("1 + 2 = %s" % value)

            loop.stop()

        asyncio.set_event_loop_policy(aioeventlet.EventLoopPolicy())
        eventlet.spawn(green_sum)
        loop = asyncio.get_event_loop()
        loop.run_forever()
        loop.close()

   Output::

        computation in progress...
        computation in progress...
        computation in progress...
        1 + 2 = 3

wrap_greenthread
----------------

.. function:: wrap_greenthread(gt)

   Wrap an eventlet GreenThread, or a greenlet, into a Future object.

   The Future object waits for the completion of a greenthread. The result or
   the exception of the greenthread will be stored in the Future object.

   The greenthread must be wrapped before its execution starts.  If the
   greenthread is running or already finished, an exception is raised.

   For greenlets, the ``run`` attribute must be set.

   .. versionchanged:: 0.3

     An exception is now raised if the greenthread is running or already
     finished. In debug mode, the exception is not more logged to sys.stderr
     for greenthreads.

   Example of trollius coroutine waiting for a greenthread. The ``progress()``
   callback is called regulary to see that the event loop in not blocked::

        import aioeventlet
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
            loop.call_soon(progress)

            gt = eventlet.spawn(slow_sum, 1, 2)
            fut = aioeventlet.wrap_greenthread(gt, loop=loop)

            result = yield From(fut)
            print("1 + 2 = %s" % result)

        asyncio.set_event_loop_policy(aioeventlet.EventLoopPolicy())
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

Install aioeventlet with pip
----------------------------

Type::

    pip install aioeventlet

Install aioeventlet on Windows with pip
---------------------------------------

Procedure for Python 2.7:

* If pip is not installed yet, `install pip
  <http://www.pip-installer.org/en/latest/installing.html>`_: download
  ``get-pip.py`` and type::

  \Python27\python.exe get-pip.py

* Install aioeventlet with pip::

  \Python27\python.exe -m pip install aioeventlet

* pip also installs dependencies: ``eventlet`` and ``trollius``

Manual installation of aioeventlet
----------------------------------

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

The `tox project <http://testrun.org/tox/latest/>`_ can be used to build a
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

To run unit tests, the ``mock`` module is need on Python older than 3.3.

Run the following command::

    python runtests.py -r
