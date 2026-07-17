import logging
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class TimelineEngine:
    """Timeline engine to record chronological operational actions.

    Uses Redis Streams (XADD/XREVRANGE) to provide a fast, ordered timeline
    of events (Missions, Incidents, Resource Assignments).
    """

    def __init__(self, redis_url: str):
        self.redis = Redis.from_url(redis_url, decode_responses=True)
        self.STREAM_KEY = "timeline:events"

    async def record_event(self, venue_id: str, event_type: str, payload: dict[str, Any]) -> None:
        """Record an event into the timeline stream."""
        entry = {
            "venue_id": venue_id,
            "event_type": event_type,
            # We stringify the payload for Redis stream fields
            "payload": str(payload),
        }
        await self.redis.xadd(self.STREAM_KEY, entry)
        logger.info(f"Recorded timeline event: {event_type} for venue {venue_id}")

    async def get_timeline(self, venue_id: str, count: int = 50) -> list[dict[str, Any]]:
        """Fetch the most recent events from the timeline for a venue."""
        # Get newest first
        results = await self.redis.xrevrange(self.STREAM_KEY, max="+", min="-", count=count * 5)
        timeline = []

        for message_id, data in results:
            if data.get("venue_id") == venue_id:
                timeline.append(
                    {
                        "id": message_id,
                        "event_type": data.get("event_type"),
                        "payload": data.get("payload"),
                    }
                )
            if len(timeline) >= count:
                break

        return timeline
