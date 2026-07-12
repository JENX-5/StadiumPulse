"""
Event Bus -> WebSocket bridge.

`EventBus` (Redis pub/sub) and `ws_manager` (browser-facing WebSocket
connections) previously had no wiring between them: publishers wrote to
Redis, but nothing ever read it back out to connected clients. This module
is that missing link — one background task per channel, each relaying
every event it receives straight to `ws_manager.broadcast()` as JSON.

Started once as a background task in `main.py`'s lifespan and run for the
lifetime of the process; cancelled on shutdown.
"""

from __future__ import annotations

import asyncio

import structlog

from app.api.websockets.manager import ws_manager
from app.core.events import EventChannel
from app.services.event_bus import EventBus

logger = structlog.get_logger(__name__)


async def _relay_channel(event_bus: EventBus, channel: EventChannel) -> None:
    async for event in event_bus.subscribe(channel):
        try:
            await ws_manager.broadcast(event.to_json())
        except Exception:  # pragma: no cover - defensive, a bad client shouldn't kill the relay
            logger.error("event_relay_broadcast_failed", channel=channel.value)


async def run_event_bridge(event_bus: EventBus) -> None:
    """Relay every channel concurrently until cancelled."""
    logger.info("event_bridge_starting", channels=[c.value for c in EventChannel])
    await asyncio.gather(
        *(_relay_channel(event_bus, channel) for channel in EventChannel),
        return_exceptions=True,
    )
