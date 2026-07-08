"""
AgentRegistry: the directory of every agent instance available in the
running process.

Module 3 ships this empty (see `Container.agent_registry` in
`core/container.py`) — later modules import their concrete `BaseAgent`
subclass and call `registry.register(MyAgent())` during their own startup
wiring. The orchestrator only ever looks agents up by `agent_id` through
this registry, never imports a concrete agent class itself.
"""

from __future__ import annotations

import structlog

from app.agents.base import BaseAgent
from app.agents.exceptions import AgentNotFoundError

logger = structlog.get_logger(__name__)


class AgentRegistry:
    """In-process directory of registered `BaseAgent` instances."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent, *, replace: bool = False) -> None:
        if not replace and agent.agent_id in self._agents:
            raise ValueError(
                f"Agent '{agent.agent_id}' is already registered "
                "(pass replace=True to intentionally overwrite it)"
            )
        self._agents[agent.agent_id] = agent
        logger.info("agent_registered", agent_id=agent.agent_id, name=agent.name)

    def unregister(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)
        logger.info("agent_unregistered", agent_id=agent_id)

    def get(self, agent_id: str) -> BaseAgent:
        agent = self._agents.get(agent_id)
        if agent is None:
            raise AgentNotFoundError(f"No agent registered with id '{agent_id}'")
        return agent

    def has(self, agent_id: str) -> bool:
        return agent_id in self._agents

    def list_agents(self) -> list[BaseAgent]:
        return list(self._agents.values())

    def find_by_task(self, task_type: str) -> list[BaseAgent]:
        """Discovery helper: which registered agents claim to support this task_type."""
        return [a for a in self._agents.values() if task_type in a.supported_tasks]

    def capabilities(self) -> dict[str, dict[str, object]]:
        """Metadata snapshot for every registered agent — the shape a
        `GET /agents` diagnostics endpoint (future module) would return."""
        return {
            agent_id: {
                "name": agent.name,
                "description": agent.description,
                "supported_tasks": list(agent.supported_tasks),
            }
            for agent_id, agent in self._agents.items()
        }

    async def health_status(self) -> dict[str, dict[str, object]]:
        """Run every registered agent's `health_check()` concurrently."""
        import asyncio

        agent_ids = list(self._agents.keys())
        results = await asyncio.gather(
            *(self._agents[aid].health_check() for aid in agent_ids),
            return_exceptions=True,
        )
        status: dict[str, dict[str, object]] = {}
        for agent_id, result in zip(agent_ids, results, strict=True):
            if isinstance(result, Exception):
                status[agent_id] = {"agent_id": agent_id, "healthy": False, "error": str(result)}
            else:
                status[agent_id] = result
        return status

    def __len__(self) -> int:
        return len(self._agents)
