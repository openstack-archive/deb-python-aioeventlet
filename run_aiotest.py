import eventlet
import sys

if '-m' in sys.argv:
    print("Enable eventlet monkey patching")
    eventlet.monkey_patch()
    sys.argv.remove('-m')

import aioeventlet
import aiotest.run

config = aiotest.TestConfig()
config.asyncio = aioeventlet.asyncio
config.socket = eventlet.patcher.original('socket')
config.threading = eventlet.patcher.original('threading')
config.sleep = eventlet.sleep
config.socketpair = aioeventlet.socketpair
config.new_event_pool_policy = aioeventlet.EventLoopPolicy
aiotest.run.main(config)
