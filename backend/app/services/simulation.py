import asyncio
import logging
import uuid
from datetime import UTC, datetime

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
        self._task: asyncio.Task | None = None

    def apply_control(self, control: SimulationControl) -> SimulationStatusResponse:
        if control.command == "start":
            self.is_running = True
            self.is_paused = False
            self.speed_multiplier = control.speed_multiplier
            self.deterministic = control.deterministic
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
        )

    async def _simulation_loop(self):
        logger.info("Simulation Engine started.")
        try:
            while self.is_running:
                if self.is_paused:
                    await asyncio.sleep(1.0)
                    continue

                # In a full implementation, we'd pull the real venue_id and generate
                # realistic simulated data (crowd density per zone, random incidents).
                # For now, we publish a simple tick event to the RISK_SCORES channel.
                event = Event(
                    event_type="simulation.tick",
                    source=EventSource.SIMULATION,
                    venue_id=str(uuid.uuid4()),  # Demo venue UUID placeholder
                    payload={
                        "timestamp": datetime.now(UTC).isoformat(),
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
