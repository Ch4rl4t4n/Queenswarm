"""Application settings for the Queenswarm bee-hive API (Pydantic v2)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration for swarm routing, hive mind storage, and governance."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # --- LLM Routing (LiteLLM: Grok primary → Claude fallback → optional OpenAI)
    grok_api_key: str = Field(..., description="Primary LLM routing key (Grok / xAI).")
    anthropic_api_key: str = Field(..., description="Fallback Claude key via LiteLLM.")
    openai_api_key: str | None = Field(default=None, description="Optional cheap-route key.")

    # --- Global Hive Mind (PostgreSQL primary store)
    postgres_url: str = Field(
        ...,
        description="Async SQLAlchemy URL, e.g. postgresql+asyncpg://user:pass@host/db",
    )
    postgres_user: str
    postgres_password: str
    postgres_db: str = "queenswarm"

    # --- Redis (queues, rate limits, waggle-dance pub/sub)
    redis_url: str

    # --- Neo4j (knowledge graph, imitation chains, decay)
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str

    # --- ChromaDB (vectors, Recipe Library semantic recall)
    chroma_host: str = "chromadb"
    chroma_port: int = 8000

    # --- Bee-hive tuning (decentralized sub-swarms → global sync cadence)
    sub_swarm_size: int = Field(
        default=8,
        ge=1,
        description="Default bees per local sub-swarm (scout/eval/sim/action override below).",
    )
    hive_sync_interval_sec: int = Field(
        default=300,
        ge=60,
        description="Interval for sub-swarms to sync state into the global hive mind.",
    )
    reward_threshold_pass: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for verified (simulated) outcomes and pollen awards.",
    )
    rapid_loop_timeout_sec: int = Field(
        default=60,
        ge=1,
        description="Budget for scrape → reflect → simulate → reward rapid learning loop.",
    )
    imitation_top_k: int = Field(
        default=3,
        ge=1,
        description="Top-K neighbors the imitation engine may copy from.",
    )
    memory_decay_days: int = Field(default=14, ge=1)
    scout_swarm_size: int = Field(default=8, ge=1)
    eval_swarm_size: int = Field(default=6, ge=1)
    sim_swarm_size: int = Field(default=5, ge=1)
    action_swarm_size: int = Field(default=10, ge=1)

    # --- Security (JWT gates all routes except exempt paths in routers)
    secret_key: str = Field(..., min_length=32, description="HS256 signing secret from env.")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # --- Domain & CORS (Bee-Hive Dashboard origin)
    domain: str = "queenswarm.love"
    cors_origins: list[str] | str = Field(
        default_factory=lambda: [
            "https://queenswarm.love",
            "https://www.queenswarm.love",
            "http://localhost:3000",
        ]
    )

    # --- Notifications (Reporter bee → humans)
    slack_webhook_url: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_pass: str | None = None
    notion_api_key: str | None = None

    # --- Scraping inputs (scout swarm ingestion)
    youtube_api_key: str | None = None
    user_agent: str = "QueenswarmBot/2.0"
    proxy_list_url: str | None = None

    # --- Cost Governor (LLM/spend rails before simulation fan-out)
    daily_budget_usd: float = 10.0
    weekly_budget_usd: float = 50.0
    monthly_budget_usd: float = 200.0
    cost_warning_threshold: float = Field(default=0.8, ge=0.0, le=1.0)

    # --- Auto Workflow Breaker (LiteLLM decomposition router)
    workflow_breaker_primary_model: str = "xai/grok-2-latest"
    workflow_breaker_fallback_model: str = "anthropic/claude-3-5-sonnet-latest"
    workflow_breaker_max_output_tokens: int = 4096
    workflow_breaker_temperature: float = 0.15
    @classmethod
    def split_cors_origins(cls, value: list[str] | str) -> list[str]:
        """Normalize ``CORS_ORIGINS`` from CSV strings or typed lists."""

        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return list(value)


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings singleton (immutable for the process lifetime).

    Returns:
        Fully resolved Settings from environment variables and optional `.env` file.

    Raises:
        ValidationError: If required secrets or URLs are missing or invalid.
    """

    return Settings()


settings: Settings = get_settings()
