import eventlet
import tests

class EventletTests(tests.TestCase):
    def test_stop(self):
        def func():
            eventlet.spawn(self.loop.call_soon_threadsafe, self.loop.stop)

        def schedule_greenthread():
            eventlet.spawn(func)

        self.loop.call_soon(schedule_greenthread)
        self.loop.run_forever()

    def test_soon(self):
        result = []

        def func():
            result.append("spawn")
            self.loop.call_soon_threadsafe(self.loop.stop)

        def schedule_greenthread():
            eventlet.spawn(func)

        self.loop.call_soon(schedule_greenthread)
        self.loop.run_forever()
        self.assertEqual(result, ["spawn"])

    def test_soon_spawn(self):
        result = []

        def func1():
            result.append("spawn")

        def func2():
            result.append("spawn_after")
            self.loop.call_soon_threadsafe(self.loop.stop)

        def schedule_greenthread():
            eventlet.spawn(func1)
            eventlet.spawn_after(0.010, func2)

        self.loop.call_soon(schedule_greenthread)
        self.loop.run_forever()
        self.assertEqual(result, ["spawn", "spawn_after"])


if __name__ == '__main__':
    import unittest
    unittest.main()
