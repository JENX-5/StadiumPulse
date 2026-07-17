"""Tests for Settings' fail-fast production guard (core/config.py)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_rejects_dev_fallback_jwt_secret_in_production() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(ENV="production", JWT_SECRET="fallback_secret_for_development_only_please_change")


def test_rejects_short_jwt_secret_in_production() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(ENV="production", JWT_SECRET="too-short")


def test_accepts_strong_jwt_secret_in_production() -> None:
    settings = Settings(ENV="production", JWT_SECRET="a" * 40)
    assert settings.env == "production"


def test_dev_fallback_jwt_secret_is_fine_outside_production() -> None:
    # Doesn't matter what secret is in play outside production -- the guard
    # is scoped to ENV=production only.
    settings = Settings(
        ENV="development", JWT_SECRET="fallback_secret_for_development_only_please_change"
    )
    assert settings.env == "development"
