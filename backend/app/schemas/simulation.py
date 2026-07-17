from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SimulationControl(BaseModel):
    """Schema for controlling the Simulation Engine state."""

    command: Literal["start", "stop", "pause", "resume"] = Field(
        ..., description="Action to perform on the simulation"
    )
    venue_id: str | None = Field(
        default=None,
        description="Venue the simulation should tick against. Required on 'start'; "
        "carried over from the last 'start' for subsequent pause/resume/stop calls.",
    )
    speed_multiplier: float = Field(default=1.0, description="1.0 is real-time, higher is faster")
    deterministic: bool = Field(
        default=False, description="If true, use a fixed seed for reproducible events"
    )
    random_seed: int | None = Field(
        default=None, description="Optional seed for deterministic mode"
    )


class SimulationStatusResponse(BaseModel):
    """Schema for returning the current state of the simulation engine."""

    is_running: bool
    is_paused: bool
    speed_multiplier: float
    deterministic: bool
    venue_id: str | None = None
