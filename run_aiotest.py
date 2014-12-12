#import eventlet; eventlet.monkey_patch()

import aioeventlet
import aiotest.run
import eventlet

config = aiotest.TestConfig()
config.asyncio = aioeventlet.asyncio
config.socket = eventlet.patcher.original('socket')
config.threading = eventlet.patcher.original('threading')
config.sleep = eventlet.sleep
config.socketpair = aioeventlet.socketpair
config.new_event_pool_policy = aioeventlet.EventLoopPolicy
aiotest.run.main(config)
