"""
Queue infrastructure for legal platform.

Configures Dramatiq with a Redis broker for background job processing.
All worker tasks should import the broker from this module to ensure
proper registration.

.. warning::
   DEPLOYMENT RISK: The Dramatiq queue backend must be configured with a running Redis instance before any workers or producers can function.
   Required: Redis instance reachable at the configured REDIS_URL.
   Impact if missing: All background job enqueueing will fail; workers will not receive tasks and job status will never progress from 'pending'.
"""

import os

import dramatiq
from dramatiq.brokers.redis import RedisBroker


redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
broker = RedisBroker(url=redis_url)
dramatiq.set_broker(broker)
