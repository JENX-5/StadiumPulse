import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.core.events import Event, EventChannel, EventSource
from app.schemas.simulation import SimulationControl, SimulationStatusResponse
from app.services.event_bus import EventBus

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Background simulator generating stadium traffic, crowd density, and mock incidents.

    This engine publishes strictly EventSource.SIMULATION events to the Event Bus
    so that downstream agents can train/test without contaminating live operational data.
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.is_running = False
        self.is_paused = False
        self.speed_multiplier = 1.0
        self.deterministic = False
        # Set on "start" (and required there); carried over across
        # pause/resume/stop so every tick in a run targets the same venue.
        self.venue_id: str | None = None
        self._task: asyncio.Task | None = None

    def apply_control(self, control: SimulationControl) -> SimulationStatusResponse:
        if control.command == "start":
            self.is_running = True
            self.is_paused = False
            self.speed_multiplier = control.speed_multiplier
            self.deterministic = control.deterministic
            # Fall back to whatever venue was last used rather than silently
            # generating a random one — a client that starts without a
            # venue_id almost certainly meant to reuse the current session.
            self.venue_id = control.venue_id or self.venue_id
            if self._task is None or self._task.done():
                self._task = asyncio.create_task(self._simulation_loop())

        elif control.command == "stop":
            self.is_running = False
            self.is_paused = False
            if self._task and not self._task.done():
                self._task.cancel()

        elif control.command == "pause":
            self.is_paused = True

        elif control.command == "resume":
            self.is_paused = False
            self.speed_multiplier = control.speed_multiplier

        return self.get_status()

    def get_status(self) -> SimulationStatusResponse:
        return SimulationStatusResponse(
            is_running=self.is_running,
            is_paused=self.is_paused,
            speed_multiplier=self.speed_multiplier,
            deterministic=self.deterministic,
            venue_id=self.venue_id,
        )

    async def _simulation_loop(self):
        logger.info(f"Simulation Engine started for venue={self.venue_id}.")
        try:
            while self.is_running:
                if self.is_paused:
                    await asyncio.sleep(1.0)
                    continue

                # In a full implementation, we'd generate realistic simulated
                # data per zone (crowd density per zone, random incidents).
                # For now, we publish a simple tick event to the RISK_SCORES channel.
                event = Event(
                    event_type="simulation.tick",
                    source=EventSource.SIMULATION,
                    venue_id=self.venue_id or str(uuid.uuid4()),
                    payload={
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "global_crowd_density": 0.85,
                        "global_noise_level": 82.5,
                    },
                )
                await self.event_bus.publish(EventChannel.RISK_SCORES, event)

                # Base tick rate is 5 seconds, adjusted by speed_multiplier
                sleep_duration = 5.0 / max(0.1, self.speed_multiplier)
                await asyncio.sleep(sleep_duration)
        except asyncio.CancelledError:
            logger.info("Simulation Engine stopped.")
        except Exception as e:
            logger.error(f"Simulation Engine crashed: {e}")
            self.is_running = False
