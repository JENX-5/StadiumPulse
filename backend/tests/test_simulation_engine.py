"""Tests for SimulationEngine: the background task that publishes
EventSource.SIMULATION traffic onto the Event Bus (see services/simulation.py
docstring — this must never be mistaken for live operational data)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.core.events import EventChannel, EventSource
from app.schemas.simulation import SimulationControl
from app.services.simulation import SimulationEngine


@pytest.fixture
def event_bus() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def engine(event_bus: AsyncMock) -> SimulationEngine:
    return SimulationEngine(event_bus=event_bus)


async def _stop_and_wait(engine: SimulationEngine) -> None:
    """Cleanly tear down any background task the test started, so it can't
    leak into (or fail) a later test."""
    engine.apply_control(SimulationControl(command="stop"))
    if engine._task is not None:
        try:
            await asyncio.wait_for(asyncio.shield(engine._task), timeout=1.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass


@pytest.mark.asyncio
async def test_initial_status_is_idle(engine: SimulationEngine) -> None:
    status = engine.get_status()
    assert status.is_running is False
    assert status.is_paused is False
    assert status.speed_multiplier == 1.0
    assert status.venue_id is None


@pytest.mark.asyncio
async def test_start_requires_and_stores_venue_id(engine: SimulationEngine) -> None:
    engine.apply_control(SimulationControl(command="start", venue_id="venue-1"))
    try:
        status = engine.get_status()
        assert status.is_running is True
        assert status.is_paused is False
        assert status.venue_id == "venue-1"
    finally:
        await _stop_and_wait(engine)


@pytest.mark.asyncio
async def test_start_without_venue_id_reuses_last_venue(engine: SimulationEngine) -> None:
    """A client that starts without a venue_id almost certainly meant to
    reuse the current session (per the inline comment in apply_control)."""
    engine.apply_control(SimulationControl(command="start", venue_id="venue-1"))
    await _stop_and_wait(engine)

    engine.apply_control(SimulationControl(command="start", venue_id=None))
    try:
        assert engine.get_status().venue_id == "venue-1"
    finally:
        await _stop_and_wait(engine)


@pytest.mark.asyncio
async def test_stop_cancels_running_task(engine: SimulationEngine) -> None:
    engine.apply_control(SimulationControl(command="start", venue_id="venue-1"))
    task = engine._task
    assert task is not None

    status = engine.apply_control(SimulationControl(command="stop"))

    assert status.is_running is False
    assert status.is_paused is False
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_pause_stops_ticking_without_cancelling_task(engine: SimulationEngine) -> None:
    engine.apply_control(SimulationControl(command="start", venue_id="venue-1"))
    try:
        engine.apply_control(SimulationControl(command="pause"))
        status = engine.get_status()
        assert status.is_paused is True
        assert status.is_running is True
        assert not engine._task.done()
    finally:
        await _stop_and_wait(engine)


@pytest.mark.asyncio
async def test_resume_clears_pause_and_applies_new_speed(engine: SimulationEngine) -> None:
    engine.apply_control(SimulationControl(command="start", venue_id="venue-1"))
    try:
        engine.apply_control(SimulationControl(command="pause"))
        status = engine.apply_control(SimulationControl(command="resume", speed_multiplier=4.0))
        assert status.is_paused is False
        assert status.speed_multiplier == 4.0
    finally:
        await _stop_and_wait(engine)


@pytest.mark.asyncio
async def test_starting_twice_does_not_spawn_a_second_task(engine: SimulationEngine) -> None:
    engine.apply_control(SimulationControl(command="start", venue_id="venue-1"))
    first_task = engine._task
    engine.apply_control(SimulationControl(command="start", venue_id="venue-1"))
    try:
        assert engine._task is first_task
    finally:
        await _stop_and_wait(engine)


@pytest.mark.asyncio
async def test_tick_publishes_to_risk_scores_channel_as_simulation_source(
    engine: SimulationEngine, event_bus: AsyncMock
) -> None:
    engine.apply_control(
        SimulationControl(command="start", venue_id="venue-1", speed_multiplier=1000.0)
    )
    try:
        for _ in range(50):
            if event_bus.publish.await_count:
                break
            await asyncio.sleep(0.01)
        assert event_bus.publish.await_count >= 1

        channel, event = event_bus.publish.await_args.args
        assert channel == EventChannel.RISK_SCORES
        assert event.source == EventSource.SIMULATION
        assert event.venue_id == "venue-1"
        assert event.event_type == "simulation.tick"
    finally:
        await _stop_and_wait(engine)


@pytest.mark.asyncio
async def test_publish_failure_stops_the_loop(
    engine: SimulationEngine, event_bus: AsyncMock
) -> None:
    """Current behavior: the loop's blanket except logs and sets is_running
    False on the first unhandled publish error, rather than retrying — this
    test pins that behavior so a future change to it is deliberate."""
    event_bus.publish.side_effect = RuntimeError("redis down")
    engine.apply_control(
        SimulationControl(command="start", venue_id="venue-1", speed_multiplier=1000.0)
    )
    try:
        for _ in range(50):
            if not engine.is_running:
                break
            await asyncio.sleep(0.01)
        assert engine.is_running is False
    finally:
        await _stop_and_wait(engine)
