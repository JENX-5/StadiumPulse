"""Verifies the SlowAPI rate limiter actually rejects excess traffic when
enabled -- the test suite itself runs with it disabled (see conftest.py's
`ENV=test` default) since the ASGI test transport shares one synthetic
client address across the whole session, so this test builds its own
short-lived app instance with rate limiting explicitly turned on."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_rate_limiter_rejects_requests_over_the_budget() -> None:
    from app.core.config import Settings
    from app.core.container import build_container
    from app.main import create_app

    # `Settings`'s fields are alias-populated (`alias="ENV"` etc, no
    # `populate_by_name`), so the constructor must use the alias names --
    # passing the lowercase field names is silently ignored (`extra="ignore"`)
    # and the values fall through to the process env / .env file instead.
    settings = Settings(
        ENV="production", 
        HTTP_RATE_LIMIT="5/minute",
        JWT_SECRET="dummy_secret_for_testing_purposes_that_is_long_enough_32_chars_plus"
    )
    app = create_app(settings=settings)
    app.state.container = await build_container(settings)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            statuses = [(await ac.get("/health")).status_code for _ in range(8)]
    finally:
        await app.state.container.shutdown()

    assert statuses[:5] == [200] * 5
    assert 429 in statuses[5:]
