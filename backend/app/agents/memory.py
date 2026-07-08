"""
Memory abstractions (Module 3 scope: interface + a simple in-process
provider only).

`app.db.models.tournament_memory.TournamentMemory` already exists at the
DB layer (Module 2) with a pgvector embedding column — but the *agent* that
writes/queries it (embedding generation, similarity search, "pattern
recognized" narrative) is explicitly a future module. `MemoryInterface`
here is the seam that future module will implement; `InMemoryMemoryStore`
is a working, dependency-free provider so orchestrator/negotiation code
can be built and tested against a real (if non-persistent) implementation
today.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from app.agents.types import AgentMemory


class MemoryInterface(ABC):
    """Contract every memory backend (in-process, Redis, pgvector-backed
    Tournament Memory) must implement."""

    @abstractmethod
    async def store(
        self, key: str, content: str, *, metadata: dict[str, Any] | None = None
    ) -> None: ...

    @abstractmethod
    async def get(self, key: str) -> AgentMemory | None: ...

    @abstractmethod
    async def query(
        self, *, filters: dict[str, Any] | None = None, limit: int = 10
    ) -> list[AgentMemory]:
        """Return memories matching `filters` (exact-match on metadata keys
        for this simple provider). A future pgvector-backed provider would
        instead accept a query embedding and return the nearest neighbors —
        same return type, different retrieval strategy."""

    @abstractmethod
    async def delete(self, key: str) -> None: ...


class InMemoryMemoryStore(MemoryInterface):
    """Process-local, non-persistent `MemoryInterface` implementation.

    Suitable for tests and for local development before a real memory
    backend is wired in. Not suitable for production use across multiple
    backend instances — state lives only in this process's dict.
    """

    def __init__(self) -> None:
        self._items: dict[str, AgentMemory] = {}
        self._stored_at: dict[str, datetime] = {}

    async def store(
        self, key: str, content: str, *, metadata: dict[str, Any] | None = None
    ) -> None:
        self._items[key] = AgentMemory(memory_id=key, content=content, metadata=metadata or {})
        self._stored_at[key] = datetime.now(UTC)

    async def get(self, key: str) -> AgentMemory | None:
        return self._items.get(key)

    async def query(
        self, *, filters: dict[str, Any] | None = None, limit: int = 10
    ) -> list[AgentMemory]:
        filters = filters or {}
        results = [
            item
            for item in self._items.values()
            if all(item.metadata.get(k) == v for k, v in filters.items())
        ]
        # Most-recently-stored first, since this provider has no relevance score.
        results.sort(
            key=lambda item: self._stored_at.get(item.memory_id, datetime.min), reverse=True
        )
        return results[:limit]

    async def delete(self, key: str) -> None:
        self._items.pop(key, None)
        self._stored_at.pop(key, None)


class MemoryProvider:
    """Thin namespacing wrapper around a `MemoryInterface`.

    Agents shouldn't have to build their own key-prefixing scheme to avoid
    colliding with other agents' entries in a shared backend; this does it
    for them.
    """

    def __init__(self, backend: MemoryInterface, *, namespace: str) -> None:
        self._backend = backend
        self._namespace = namespace

    def _scoped(self, key: str) -> str:
        return f"{self._namespace}:{key}"

    async def store(
        self, key: str, content: str, *, metadata: dict[str, Any] | None = None
    ) -> None:
        await self._backend.store(self._scoped(key), content, metadata=metadata)

    async def get(self, key: str) -> AgentMemory | None:
        return await self._backend.get(self._scoped(key))

    async def query(
        self, *, filters: dict[str, Any] | None = None, limit: int = 10
    ) -> list[AgentMemory]:
        return await self._backend.query(filters=filters, limit=limit)

    async def delete(self, key: str) -> None:
        await self._backend.delete(self._scoped(key))
