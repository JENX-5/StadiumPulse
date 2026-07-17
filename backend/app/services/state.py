import json
import logging
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class OperationalStateManager:
    """Maintains the real-time stadium state hot-cache using Redis.

    This service tracks active incidents, crowd density, and resource statuses
    so the frontend and AI agents can query the current state without hitting
    the primary Postgres database heavily.
    """

    def __init__(self, redis_url: str):
        self.redis = Redis.from_url(redis_url, decode_responses=True)
        self.STATE_PREFIX = "state:venue:"

    async def get_state(self, venue_id: str) -> dict[str, Any]:
        """Fetch the current operational state for a venue."""
        key = f"{self.STATE_PREFIX}{venue_id}"
        state_json = await self.redis.get(key)
        if state_json:
            return json.loads(state_json)

        # Default empty state if not initialized
        return {
            "venue_id": venue_id,
            "active_incidents": 0,
            "global_crowd_density": 0.0,
            "global_noise_level": 0.0,
            "available_resources": 0,
        }

    async def update_state(self, venue_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Merge updates into the current operational state."""
        key = f"{self.STATE_PREFIX}{venue_id}"

        # Read-modify-write (in a production environment, we'd use Redis JSON or Lua script)
        current_state = await self.get_state(venue_id)
        current_state.update(updates)

        await self.redis.set(key, json.dumps(current_state))
        logger.info(f"Updated operational state for venue {venue_id}")
        return current_state
