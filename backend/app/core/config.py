"""
Centralized application configuration.

All environment-driven values flow through this single `Settings` object so
that no module reads `os.environ` directly. This keeps configuration
testable (override via `Settings(**overrides)`) and gives us one place to
validate required values at startup instead of failing deep in a request.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings, populated from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Environment ---------------------------------------------------------
    env: Literal["development", "staging", "production", "test"] = Field(
        default="development", alias="ENV"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # --- Database --------------------------------------------------------------
    database_url: str = Field(
        default="postgresql+asyncpg://stadiumpulse:stadiumpulse@localhost:5432/stadiumpulse",
        alias="DATABASE_URL",
    )
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=5, alias="DB_MAX_OVERFLOW")

    # --- Redis -------------------------------------------------------------------
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # --- LLM ---------------------------------------------------------------------
    # `llm_provider` selects which LLMClient implementation the factory
    # (app.core.llm_providers.build_llm_client) constructs. Module 3 adds
    # OpenAI/Gemini as swappable alternatives to Anthropic per the Agent
    # Framework's provider-abstraction requirement; agents never import a
    # concrete client, only `app.core.llm_client.LLMClient`.
    llm_provider: Literal["anthropic", "openai", "gemini"] = Field(
        default="gemini", alias="LLM_PROVIDER"
    )
    llm_max_retries: int = Field(default=1, alias="LLM_MAX_RETRIES")
    llm_timeout_seconds: float = Field(default=20.0, alias="LLM_TIMEOUT_SECONDS")
    # Requests-per-minute budget applied uniformly to whichever provider is
    # active (RateLimitedLLMClient wraps every provider the same way).
    llm_rate_limit_per_minute: int = Field(default=60, alias="LLM_RATE_LIMIT_PER_MINUTE")

    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model_default: str = Field(
        default="claude-sonnet-4-6", alias="ANTHROPIC_MODEL_DEFAULT"
    )
    anthropic_model_escalation: str = Field(
        default="claude-opus-4-8", alias="ANTHROPIC_MODEL_ESCALATION"
    )

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model_default: str = Field(default="gpt-4o", alias="OPENAI_MODEL_DEFAULT")

    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model_default: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL_DEFAULT")

    # --- Auth ------------------------------------------------------------------
    jwt_secret: str = Field(default="fallback_secret_for_development_only_please_change", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=1440, alias="JWT_EXPIRE_MINUTES")

    # --- API ---------------------------------------------------------------------
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:3001", alias="CORS_ORIGINS")

    @field_validator("database_url")
    @classmethod
    def fix_sqlalchemy_dialect(cls, value: str) -> str:
        # Render and Heroku provide connection strings starting with postgres:// or postgresql://
        # We must use asyncpg for SQLAlchemy's async engine.
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://") and not value.startswith("postgresql+asyncpg://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @field_validator("gemini_api_key")
    @classmethod
    def warn_on_missing_llm_key(cls, value: str) -> str:
        # We do not raise here: health checks and non-agent endpoints must still
        # function in local/dev setups where the key isn't configured yet.
        # The LLMClient itself raises a clear error if a key-dependent call is made.
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton.

    Cached via lru_cache so Settings is parsed once per process, not once
    per request — env parsing is cheap but this keeps the pattern consistent
    with how the DI container resolves other singletons.
    """
    return Settings()
