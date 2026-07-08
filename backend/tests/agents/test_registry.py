from __future__ import annotations

import pytest

from app.agents.exceptions import AgentNotFoundError
from app.agents.registry import AgentRegistry
from tests.agents.conftest import AlwaysFailsAgent, AlwaysSucceedsAgent


def test_register_and_get():
    registry = AgentRegistry()
    agent = AlwaysSucceedsAgent()
    registry.register(agent)

    assert registry.get("always_succeeds") is agent
    assert len(registry) == 1


def test_duplicate_registration_raises_without_replace():
    registry = AgentRegistry()
    registry.register(AlwaysSucceedsAgent())

    with pytest.raises(ValueError):
        registry.register(AlwaysSucceedsAgent())


def test_duplicate_registration_allowed_with_replace():
    registry = AgentRegistry()
    registry.register(AlwaysSucceedsAgent())
    registry.register(AlwaysSucceedsAgent(), replace=True)

    assert len(registry) == 1


def test_get_unknown_agent_raises_not_found():
    registry = AgentRegistry()
    with pytest.raises(AgentNotFoundError):
        registry.get("nonexistent")


def test_find_by_task():
    registry = AgentRegistry()
    succeeds = AlwaysSucceedsAgent()
    fails = AlwaysFailsAgent()
    registry.register(succeeds)
    registry.register(fails)

    found = registry.find_by_task("do_thing")
    assert {a.agent_id for a in found} == {"always_succeeds", "always_fails"}


def test_capabilities_snapshot():
    registry = AgentRegistry()
    registry.register(AlwaysSucceedsAgent())

    caps = registry.capabilities()
    assert caps["always_succeeds"]["supported_tasks"] == ["do_thing"]


@pytest.mark.asyncio
async def test_health_status_aggregates_all_agents():
    registry = AgentRegistry()
    registry.register(AlwaysSucceedsAgent())
    registry.register(AlwaysFailsAgent())

    status = await registry.health_status()
    assert set(status.keys()) == {"always_succeeds", "always_fails"}
    assert all(v["healthy"] for v in status.values())
