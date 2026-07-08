import logging
from typing import AsyncGenerator

from redis.asyncio import Redis

from app.core.events import Event, EventChannel

logger = logging.getLogger(__name__)


class EventBus:
    """Internal Event Bus built on Redis Pub/Sub for realtime event dispatch."""

    def __init__(self, redis_url: str):
        # We use decode_responses=True so that messages come back as strings, not bytes
        self.redis = Redis.from_url(redis_url, decode_responses=True)

    async def publish(self, channel: EventChannel, event: Event) -> None:
        """Publish an Event to a specific Redis channel."""
        try:
            # event.to_json() returns the JSON representation of the Pydantic model
            await self.redis.publish(channel.value, event.to_json())
            logger.info(f"Published event {event.event_type} to {channel.value}")
        except Exception as e:
            logger.error(f"Failed to publish event to {channel.value}: {e}")
            raise

    async def subscribe(self, channel: EventChannel) -> AsyncGenerator[Event, None]:
        """Subscribe to a Redis channel and yield Events as they arrive."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel.value)
        logger.info(f"Subscribed to {channel.value}")

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event = Event.from_json(message["data"])
                        yield event
                    except Exception as e:
                        logger.error(f"Failed to parse event from {channel.value}: {e}")
        finally:
            await pubsub.unsubscribe(channel.value)
            await pubsub.close()


# We will initialize the actual singleton instance in main.py or dependencies.py
