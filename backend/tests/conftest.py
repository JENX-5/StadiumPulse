"""
Shared pytest fixtures.

`client` gives every test module an `httpx.AsyncClient` wired to the FastAPI
app via ASGI transport (no real network socket, no running server needed).
"""

from __future__ import annotations

import os

# Must be set before `app.main` (and therefore `app.core.config.get_settings`,
# which is `@lru_cache`d) is ever imported: it's what tells `create_app()` to
# build its SlowAPI rate limiter in `enabled=False` mode. Without this, every
# test in the suite shares one process-lifetime request bucket (the ASGI test
# transport always presents the same synthetic client address), so a full
# run trips the same per-IP limit real abusive traffic is meant to hit --
# rate limiting a test run verifies nothing and only makes the suite flaky.
os.environ.setdefault("ENV", "test")

from collections.abc import AsyncGenerator  # noqa: E402

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    from app.core.config import get_settings
    from app.core.container import build_container
    from app.main import app

    app.state.container = await build_container(get_settings())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await app.state.container.shutdown()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    from sqlalchemy import text

    from app.core.config import get_settings
    from app.db.session import Base, create_engine

    settings = get_settings()
    engine = create_engine(settings)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(client: AsyncClient) -> AsyncGenerator:
    from app.main import app

    async with app.state.container.db_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def make_auth_headers(db_session):
    """Factory fixture: create a user with a given role and return
    `Authorization` headers carrying a real, signed JWT for that user —
    exercises the actual `get_current_user`/`RequireRole` path rather than
    bypassing it with a dependency override."""
    import uuid as uuid_module

    from app.core.config import get_settings
    from app.core.security import create_access_token
    from app.db.models.user import User, UserRole

    async def _make(role: UserRole = UserRole.DISPATCHER) -> dict[str, str]:
        user = User(
            id=uuid_module.uuid4(),
            email=f"{uuid_module.uuid4()}@test.stadiumpulse",
            hashed_password="not-used-in-tests",
            full_name="Test User",
            role=role,
        )
        db_session.add(user)
        await db_session.commit()
        token = create_access_token(subject=user.id, role=role.value, settings=get_settings())
        return {"Authorization": f"Bearer {token}"}

    return _make
