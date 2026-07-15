"""
Shared pytest fixtures.

`client` gives every test module an `httpx.AsyncClient` wired to the FastAPI
app via ASGI transport (no real network socket, no running server needed).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    from app.main import app
    from app.core.config import get_settings
    from app.core.container import build_container
    app.state.container = await build_container(get_settings())
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
        
    await app.state.container.shutdown()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    from app.core.config import get_settings
    from app.db.session import create_engine, Base
    import app.db.models  # Ensures all models are registered
    from sqlalchemy import text
    
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
