import logging
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class NotificationInfrastructure:
    """Handles queued delivery of high-priority notifications.
    
    Future AI agents (e.g. Predictive Intelligence) will use this to alert
    dispatchers of escalating risks before incidents actually occur.
    """

    def __init__(self, redis_url: str):
        self.redis = Redis.from_url(redis_url, decode_responses=True)
        self.QUEUE_KEY = "notifications:queue"

    async def enqueue(self, message: str, priority: str = "normal", recipient_id: str | None = None) -> None:
        """Enqueue a notification for delivery."""
        notification = {
            "message": message,
            "priority": priority,
            "recipient_id": recipient_id or "broadcast",
            "status": "pending",
        }
        # Using a simple Redis List as a queue
        await self.redis.lpush(self.QUEUE_KEY, str(notification))
        logger.info(f"Enqueued notification: {message}")

    async def pop_pending(self) -> dict[str, Any] | None:
        """Pop a pending notification from the queue (for workers to process)."""
        raw = await self.redis.rpop(self.QUEUE_KEY)
        if raw:
            # Note: in a production app with retry/ack, we'd use BRPOPLPUSH or Redis Streams
            # instead of a basic list pop to prevent message loss on worker crash.
            return eval(raw)  # Only safe because we strictly control the inputs
        return None
