import aiogreen
from aiogreen import socketpair

# Create a pair of connected file descriptors
rsock, wsock = socketpair()
loop = aiogreen.EventLoop()

def reader():
    data = rsock.recv(100)
    print("Received: %s" % data.decode())
    # We are done: unregister the file descriptor
    loop.remove_reader(rsock)
    # Stop the event loop
    loop.stop()

def writer():
    loop.remove_writer(wsock)

    # Simulate the reception of data from the network
    print("Send: abc")
    loop.call_soon(wsock.send, 'abc'.encode())

# Register the file descriptor for read event
loop.add_reader(rsock, reader)
loop.add_writer(wsock, writer)

# Run the event loop
loop.run_forever()

# We are done, close sockets and the event loop
rsock.close()
wsock.close()
loop.close()
