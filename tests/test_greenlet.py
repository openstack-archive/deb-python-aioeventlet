import aiogreen
import greenlet
import tests


class WrapGreenletTests(tests.TestCase):
    def test_wrap_greenlet(self):
        def func(value):
            return value * 3

        gl = greenlet.greenlet(func)
        fut = aiogreen.wrap_greenthread(gl)
        gl.switch(5)
        result = self.loop.run_until_complete(fut)
        self.assertEqual(result, 15)

    def test_wrap_greenlet_running(self):
        def func(value):
            gl = greenlet.getcurrent()
            return aiogreen.wrap_greenthread(gl)

        gl = greenlet.greenlet(func)
        self.assertRaises(RuntimeError, gl.switch, 5)

    def test_wrap_greenlet_dead(self):
        def func(value):
            return value * 3

        gl = greenlet.greenlet(func)
        gl.switch(5)
        self.assertRaises(RuntimeError, aiogreen.wrap_greenthread, gl)


if __name__ == '__main__':
    import unittest
    unittest.main()

