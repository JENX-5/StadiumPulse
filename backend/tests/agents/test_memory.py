from __future__ import annotations

import pytest

from app.agents.memory import InMemoryMemoryStore, MemoryProvider


@pytest.mark.asyncio
async def test_store_and_get():
    store = InMemoryMemoryStore()
    await store.store("k1", "some content", metadata={"venue_id": "v1"})

    item = await store.get("k1")
    assert item is not None
    assert item.content == "some content"
    assert item.metadata["venue_id"] == "v1"


@pytest.mark.asyncio
async def test_get_missing_key_returns_none():
    store = InMemoryMemoryStore()
    assert await store.get("nope") is None


@pytest.mark.asyncio
async def test_query_filters_by_metadata():
    store = InMemoryMemoryStore()
    await store.store("k1", "a", metadata={"venue_id": "v1"})
    await store.store("k2", "b", metadata={"venue_id": "v2"})

    results = await store.query(filters={"venue_id": "v1"})
    assert len(results) == 1
    assert results[0].content == "a"


@pytest.mark.asyncio
async def test_delete_removes_item():
    store = InMemoryMemoryStore()
    await store.store("k1", "a")
    await store.delete("k1")
    assert await store.get("k1") is None


@pytest.mark.asyncio
async def test_memory_provider_namespaces_keys():
    store = InMemoryMemoryStore()
    provider_a = MemoryProvider(store, namespace="agent_a")
    provider_b = MemoryProvider(store, namespace="agent_b")

    await provider_a.store("k1", "from a")
    await provider_b.store("k1", "from b")

    assert (await provider_a.get("k1")).content == "from a"
    assert (await provider_b.get("k1")).content == "from b"
