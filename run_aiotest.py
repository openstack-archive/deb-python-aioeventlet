import aioeventlet
import aiotest.run
import eventlet

config = aiotest.TestConfig()
config.new_event_pool_policy = aioeventlet.EventLoopPolicy
config.sleep = eventlet.sleep
aiotest.run.main(config)
