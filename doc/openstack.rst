asyncio in OpenStack
====================

.. warning::
   The project of replacing eventlet with trollius using aioeventlet in
   OpenStack is abandonned. It might done "later" when Python 2 support
   will be removed from OpenStack which is not going to happen in a near
   future.

First part (in progress): add support for trollius coroutines
-------------------------------------------------------------

Prepare OpenStack (Oslo Messaging) to support trollius coroutines using
``yield``: explicit asynchronous programming. Eventlet is still supported,
used by default, and applications and libraries don't need to be modified at
this point.

Already done:

* Write the trollius project: port asyncio to Python 2
* Stabilize trollius API
* Add trollius dependency to OpenStack
* Write the aioeventlet project to provide the asyncio API on top of eventlet

To do:

* Stabilize aioeventlet API
* Add aioeventlet dependency to OpenStack
* Write an aioeventlet executor for Oslo Messaging: rewrite greenio executor
  to replace greenio with aioeventlet

Second part (to do): rewrite code as trollius coroutines
--------------------------------------------------------

Switch from implicit asynchronous programming (eventlet using greenthreads) to
explicit asynchronous programming (trollius coroutines using ``yield``). Need
to modify OpenStack Common Libraries and applications. Modifications can be
done step by step, the switch will take more than 6 months.

The first application candidate is Ceilometer. The Ceilometer project is young,
developers are aware of eventlet issues and like Python 3, and Ceilometer don't
rely so much on asynchronous programming: most time is spent into waiting the
database anyway.

The goal is to port Ceilometer to explicit asynchronous programming during the
cycle of OpenStack Kilo.

Some applications may continue to use implicit asynchronous programming. For
example, nova is probably the most complex part beacuse it is and old project
with a lot of legacy code, it has many drivers and the code base is large.

To do:

* Ceilometer: add trollius dependency and set the trollius event loop policy to
  aioeventlet
* Ceilometer: change Oslo Messaging executor from "eventlet" to "aioeventlet"
* Redesign the service class of Oslo Incubator to support aioeventlet and/or
  trollius.  Currently, the class is designed for eventlet. The service class
  is instanciated before forking, which requires hacks on eventlet to update
  file descriptors.
* In Ceilometer and its OpenStack depedencencies: add new functions which
  are written with explicit asynchronous programming in mind (ex: trollius
  coroutines written with ``yield``).
* Rewrite Ceilometer endpoints (RPC methods) as trollius coroutines.

Questions:

* What about WSGI? aiohttp is not compatible with trollius yet.
* The quantity of code which need to be ported to asynchronous programming is
  unknown right now.
* We should be prepared to see deadlocks. OpenStack was designed for eventlet
  which implicitly switch on blocking operations. Critical sections may not be
  protected with locks, or not the right kind of lock.
* For performances, blocking operations can be executed in threads. OpenStack
  code is probably not thread-safe, which means new kinds of race conditions.
  But the code executed in threads will be explicitly scheduled to be executed
  in a thread (with ``loop.run_in_executor()``), so regressions can be easily
  identified.
* This part will take a lot of time. We may need to split it into subparts
  to have milestones, which is more attractive for developers.


Last part (to do): drop eventlet
--------------------------------

Replace aioeventlet event loop with trollius event loop, drop aioeventlet and drop
eventlet at the end.

This change will be done on applications one by one. This is no need to port
all applications at once. The work will start on Ceilometer, as a follow up
of the second part.

To do:

* Port remaining code to trollius
* Write a "trollius" executor for Oslo Messaging
* Ceilometer: Add a blocking call to ``loop.run_forever()`` in the ``main()``
  function
* Ceilometer: Replace "aioeventlet" executor with "trollius" executor
* Ceilometer: Use the standard trollius event loop policy
* Ceilometer: drop the eventlet dependency

Questions:

* Putting a blocking call to ``loop.run_forever()`` may need to redesign
  Ceilometer, this part is unclear to me right now.

Optimization, can be done later:

* Oslo Messaging: watch directly the underlying file descriptor of sockets,
  instead of using a busy loop polling the notifier
* Ceilometer: use libraries supporting directly trollius to be able to run
  parallel tasks (ex: send multiple requests to a database)


openstack-dev mailing list
--------------------------

* `[oslo] Progress of the port to Python 3
  <http://lists.openstack.org/pipermail/openstack-dev/2015-January/053846.html>`_
  (Victor Stinner, Jan 6 2015)

* `[oslo] Add a new aiogreen executor for Oslo Messaging
  <http://lists.openstack.org/pipermail/openstack-dev/2014-November/051337.html>`_
  (Victor Stinner, Nov 23 2014)

* `[oslo] Asyncio and oslo.messaging
  <http://lists.openstack.org/pipermail/openstack-dev/2014-July/039291.html>`_
  (Mark McLoughlin, Jul 3 2014)

  * `SQLAlchemy and asynchronous programming
    <http://lists.openstack.org/pipermail/openstack-dev/2014-July/039480.html>`_
    by Mike Bayer (author and maintainer of SQLAlchemy)

* `[Solum][Oslo] Next Release of oslo.messaging?
  <http://lists.openstack.org/pipermail/openstack-dev/2014-March/030304.html>`_
  (Victor Stinner, Mar 18 2014)

* `[solum] async / threading for python 2 and 3
  <http://lists.openstack.org/pipermail/openstack-dev/2014-February/027685.html>`_
  (Victor Stinner, Feb 20 2014)

* `Asynchrounous programming: replace eventlet with asyncio
  <http://lists.openstack.org/pipermail/openstack-dev/2014-February/026237.html>`_
  (Victor Stinner, Feb 4 2014)


History of asyncio in OpenStack
-------------------------------

Threads and asyncio specs:

* `Cross-project meeting: 2015-03-02
  <http://eavesdrop.openstack.org/meetings/crossproject/2015/crossproject.2015-03-03-21.02.log.html>`_
* `Cross-project meeting: 2015-02-24T21:44:05
  <http://eavesdrop.openstack.org/meetings/crossproject/2015/crossproject.2015-02-24-21.03.log.html>`_

Maybe the good one, aioeventlet project:

* March 13, 2015: Joshua Harlow wrote the spec `Replace eventlet +
  monkey-patching with ?? <https://review.openstack.org/#/c/164035/>`_
* February 17, 2015: Joshua Harlow wrote a different spec,
  `Sew over eventlet + patching with threads
  <https://review.openstack.org/#/c/156711/>`_
* February 5, 2015: new cross-project spec `Replace eventlet with asyncio
  <https://review.openstack.org/#/c/153298/>`_
* December 3, 2014: two patches posted to requirements:
  `Add aioeventlet dependency <https://review.openstack.org/#/c/138750/>`_
  and `Drop greenio dependency <https://review.openstack.org/#/c/138748/>`_.
* Novembre 23, 2014: two patches posted to Oslo Messaging:
  `Add a new aioeventlet executor <https://review.openstack.org/#/c/136653/>`_
  and `Add an optional executor callback to dispatcher
  <https://review.openstack.org/#/c/136652/>`_
* November 19, 2014: First release of the aioeventlet project

OpenStack Kilo Summit, November 3-7, 2014, at Paris:

* `Python 3 in Oslo <https://etherpad.openstack.org/p/kilo-oslo-python-3>`_:

  * add a new greenio executor to Oslo Messaging
  * port eventlet to Python 3 (with monkey-patching): see the :ref:`status of
    the eventlet port to Python 3 <eventlet-py3>`

* `What should we do about oslo.messaging?
  <https://etherpad.openstack.org/p/kilo-oslo-oslo.messaging>`_: add the new
  greenio executor

* `Python 3.4 transition <https://etherpad.openstack.org/p/py34-transition>`_

New try with a greenio executor for Oslo Messaging:

* July 29, 2014: Doug Hellmann proposed the blueprint
  `A 'greenio' executor for oslo.messaging
  <https://blueprints.launchpad.net/oslo.messaging/+spec/greenio-executor>`_,
  approved by Mark McLoughlin.
* July 24, 2014: `Add greenio dependency <https://review.openstack.org/108637>`_
  merged into openstack/requirements
* July 22, 2014: Patch `Add a new greenio executor
  <https://review.openstack.org/#/c/108652/>`_ proposed to Oslo Messaging
* July 21, 2014: Release of greenio 0.6 which is now compatible with Trollius
* July 21, 2014: Release of Trollius 1.0
* July 14, 2014: Patch `Add a 'greenio' oslo.messaging executor (spec)
  <https://review.openstack.org/#/c/104792/>`_ merged into openstack/oslo-specs.
* July 7, 2014: Patch `Fix AMQPListener for polling with timeout
  <https://review.openstack.org/#/c/104964/>`_ merged into Oslo Messaging
* July 2014: greenio executor, `[openstack-dev] [oslo] Asyncio and oslo.messaging
  <http://lists.openstack.org/pipermail/openstack-dev/2014-July/039291.html>`_

First try with a trollius executor for Oslo Messaging:

* June 20, 2014: Patch `Add an optional timeout parameter to Listener.poll
  <https://review.openstack.org/#/c/71003/>`_ merged into Oslo Messaging
* May 28, 2014: Meeting at OpenStack in action with Doug Hellman, Julien
  Danjou, Mehdi Abaakouk, Victor Stinner and Christophe to discuss the plan to
  port OpenStack to Python 3 and switch from eventlet to asyncio.
* April 23, 2014: Patch `Allow trollius 0.2
  <https://review.openstack.org/#/c/79901/>`_ merged into
  openstack/requirements
* March 21, 2014: Patch `Replace ad-hoc coroutines with Trollius coroutines
  <https://review.openstack.org/#/c/77925/>`_ proposed to Heat. Heat coroutines
  are close to Trollius coroutines. Patch abandonned, need to be rewritten,
  maybe with aioeventlet.
* February 20, 2014: The full specification of the blueprint was written:
  `Oslo/blueprints/asyncio
  <https://wiki.openstack.org/wiki/Oslo/blueprints/asyncio>`_
* February 8, 2014: Patch `Add a new dependency: trollius
  <https://review.openstack.org/#/c/70983/>`_ merged into
  openstack/requirements
* February 27, 2014: Article `Use the new asyncio module and Trollius in OpenStack
  <http://techs.enovance.com/6562/asyncio-openstack-python3>`_ published
* February 4, 2014: Patch `Add a new asynchronous executor based on Trollius
  <https://review.openstack.org/#/c/70948/>`_ proposed to Oslo Messaging,
  but it was abandonned. Running a classic Trollius event loop in a dedicated
  thread doesn't fit well into eventlet event loop.

First discussion around asyncio and OpenStack:

* December 19, 2013: Article `Why should OpenStack move to Python 3 right now?
  <http://techs.enovance.com/6521/openstack_python3>`_ published
* December 4, 2013: Blueprint `Add a asyncio executor to oslo.messaging
  <https://blueprints.launchpad.net/oslo.messaging/+spec/asyncio-executor>`_
  proposed by Flavio Percoco and accepted for OpenStack Icehouse by Mark
  McLoughlin


History of asynchronous programming in OpenStack
------------------------------------------------

In the past, the Nova project used Tornado, then Twisted and it is now using
eventlet which also became the defacto standard in OpenStack

