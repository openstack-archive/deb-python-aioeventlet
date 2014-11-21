Usage
=====

Use aiogreen with trollius
--------------------------

To support Python 2, you can use Trollius which uses ``yield`` instead
of ``yield from`` for coroutines:
http://trollius.readthedocs.org/

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


Use aiogreen with asyncio
-------------------------

aiogreen implements the asyncio API, see asyncio documentation:
https://docs.python.org/dev/library/asyncio.html

eventlet 0.15 supports Python 3 if monkey-patching is not used.

To use aiogreen with asyncio, set the event loop policy before using an event
loop, example::

    import aiogreen
    import asyncio

    asyncio.set_event_loop_policy(aiogreen.EventLoopPolicy())
    # ....

Adding this code should be enough to try examples of the asyncio documentation.

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


API
===

aiogreen specific functions:

.. function:: link_future(future)

   Wait for a future (or a task) from a greenthread.
   Return the result or raise the exception of the future.

   Example with asyncio::

       @asyncio.coroutine
       def coro_slow_sum(x, y):
           yield from asyncio.sleep(1.0)
           return x + y

       def green_sum():
           task = asyncio.async(coro_slow_sum(1, 2))
           value = aiogreen.link_future(task)
           return value

.. function:: wrap_greenthread(gt)

   Wrap a greenthread into a Future object.

   The Future object waits for the completion of a greenthread.

   Example with asyncio::

       def slow_sum(x, y):
           eventlet.sleep(1.0)
           return x + y

       @asyncio.coroutine
       def coro_sum():
           gt = eventlet.spawn(slow_sum, 1, 2)
           fut = aiogreen.wrap_greenthread(gt, loop=loop)
           result = yield from fut
           return result

   .. note::
      If the debug mode of event loop is set, when a greenthread raises an
      exception, the exception is logged to ``sys.stderr`` by eventlet, even if
      the exception is copied to the Future object as expected.


Installation
============

Requirements:

- eventlet 0.14 or newer
- asyncio or trollius:

  * Python 3.4 and newer: asyncio is now part of the stdlib
  * Python 3.3: need Tulip 0.4.1 or newer (pip install asyncio),
    but Tulip 3.4.1 or newer is recommended
  * Python 2.6-3.2: need Trollius 0.3 or newer (pip install trollius),
    but Trollius 1.0 or newer is recommended

Type::

    pip install aiogreen

or::

    python setup.py install


Run tests
=========

Run tests with tox
------------------

The `tox project <https://testrun.org/tox/latest/>`_ can be used to build a
virtual environment with all runtime and test dependencies and run tests
against different Python versions (2.6, 2.7, 3.2, 3.3).

For example, to run tests with Python 2.7, just type::

    tox -e py27

To run tests against other Python versions:

* ``py26``: Python 2.6
* ``py27``: Python 2.7
* ``py27_patch``: Python 2.7 with eventlet monkey patching
* ``py32``: Python 3.2
* ``py33``: Python 3.3
* ``py34``: Python 3.4

Run tests manually
------------------

Run the following command from the directory of the aiogreen project::

    python runtests.py -r
