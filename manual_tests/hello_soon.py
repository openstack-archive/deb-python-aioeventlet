import aiogreen

def hello_world(loop):
    print('Hello World')
    loop.stop()

loop = aiogreen.EventLoop()

# Schedule a call to hello_world()
loop.call_soon(hello_world, loop)

# Blocking call interrupted by loop.stop()
loop.run_forever()
loop.close()
