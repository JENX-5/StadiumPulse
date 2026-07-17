"""
Centralized application configuration.

All environment-driven values flow through this single `Settings` object so
that no module reads `os.environ` directly. This keeps configuration
testable (override via `Settings(**overrides)`) and gives us one place to
validate required values at startup instead of failing deep in a request.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_ONLY_JWT_SECRET = "fallback_secret_for_development_only_please_change"


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
    db_pool_size: int = Field(default=20, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")

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
    # "gemini-1.5-flash" is retired (404s on the live API). Verified directly
    # against this project's actual key: gemini-2.5-flash/2.5-flash-lite/2.0-flash
    # all 404 as "no longer available to new users" (this key's account was
    # provisioned after Google cut new accounts off from those lines), and
    # "antigravity" (a distinct agentic/coding-assistant model, not a general
    # text model) rejects `system_instruction` outright -- see
    # core/llm_providers.py's GeminiLLMClient docstring. gemini-3.5-flash is
    # the one model this key can actually reach; its free-tier quota is tight
    # (5 requests/minute, 20/day per Google's dashboard), so budget for that
    # when testing -- one incident's pipeline alone can use most of a day's
    # quota (see IncidentService._run_agent_pipeline).
    gemini_model_default: str = Field(default="gemini-3.5-flash", alias="GEMINI_MODEL_DEFAULT")
    # Used only by Tournament Memory's embed-and-store step (app/services/embeddings.py).
    # Kept separate from `gemini_model_default` since embedding and generation are
    # different model families even when both come from the same provider.
    gemini_embedding_model: str = Field(
        default="gemini-embedding-001", alias="GEMINI_EMBEDDING_MODEL"
    )

    # --- Auth ------------------------------------------------------------------
    jwt_secret: SecretStr = Field(default=SecretStr(_DEV_ONLY_JWT_SECRET), alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=1440, alias="JWT_EXPIRE_MINUTES")

    # --- API ---------------------------------------------------------------------
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:3001", alias="CORS_ORIGINS"
    )
    # Per-client-IP budget enforced by SlowAPI middleware (main.py) on top of
    # the existing per-process LLM call budget (RateLimitedLLMClient). The two
    # are independent: this one protects the HTTP surface (and DB) from being
    # hammered at all; the LLM one protects the token/cost budget specifically.
    http_rate_limit: str = Field(default="30/minute", alias="HTTP_RATE_LIMIT")

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

    @model_validator(mode="after")
    def reject_weak_production_secrets(self) -> "Settings":
        """Fail fast at startup rather than serving traffic with a secret an
        attacker can guess from this file. A deploy step that forgot to set
        `JWT_SECRET` (e.g. left Render's dashboard placeholder in place) is
        exactly the kind of misconfiguration that should crash on boot, not
        silently sign tokens anyone can forge -- same "fail fast on bad
        config" philosophy this module's docstring already commits to for
        DB/Redis."""
        if self.env == "production":
            secret = self.jwt_secret.get_secret_value()
            if secret == _DEV_ONLY_JWT_SECRET or len(secret) < 32:
                raise ValueError(
                    "JWT_SECRET must be set to a real, sufficiently long secret "
                    "(32+ chars) when ENV=production."
                )
        return self

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
