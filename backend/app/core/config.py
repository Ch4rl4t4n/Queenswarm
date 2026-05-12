"""Application settings for the Queenswarm bee-hive API (Pydantic v2)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


class Settings(BaseSettings):
    """Environment-driven configuration for swarm routing, hive mind storage, and governance."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # --- LLM Routing (LiteLLM: Grok primary → Claude fallback → optional OpenAI)
    grok_api_key: str = Field(default="", description="Primary LLM routing key (Grok / xAI); empty skips paid calls.")
    anthropic_api_key: str = Field(default="", description="Fallback Claude key via LiteLLM; empty skips that route.")
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
    celery_broker_url: str | None = Field(
        default=None,
        description="Celery broker override; defaults to redis_url when unset.",
    )
    celery_result_backend: str | None = Field(
        default=None,
        description="Celery result backend override; defaults to redis_url when unset.",
    )

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
    verified_swarm_pollen_per_bee: float = Field(
        default=1.0,
        ge=0.0,
        description=(
            "Pollen credited once per bee that executed a completed step after a verified swarm run; "
            "set to ``0`` to disable automatic grants."
        ),
    )
    expose_raw_step_outputs: bool = Field(
        default=False,
        description="When true, API surfaces internal_step_summaries for trusted operators only.",
    )
    simulator_stub_auto_verify: bool = Field(
        default=False,
        description="Dev/smoke flag: GenericBee simulator role emits synthetic passing verification.",
    )
    celery_workflow_runs_enabled: bool = Field(
        default=True,
        description="Allow POST …/run with defer_to_worker to enqueue hive.run_sub_swarm_workflow tasks.",
    )
    simulation_audit_rows_enabled: bool = Field(
        default=True,
        description="Persist simulations table audit rows after each swarm LangGraph cycle completes.",
    )
    simulation_docker_execution_enabled: bool = Field(
        default=False,
        description="When true the Docker executor may attach real container ids to Simulation rows.",
    )
    simulation_docker_image: str = Field(
        default="busybox:1.36",
        min_length=1,
        description="Image for ephemeral simulation sandbox probes (network none, capped CPU/mem).",
    )
    simulation_docker_timeout_sec: int = Field(
        default=30,
        ge=1,
        le=120,
        description="Wall-clock budget for docker create/start/rm probe sequence.",
    )
    simulation_docker_log_truncate_chars: int = Field(
        default=8192,
        ge=512,
        le=65536,
        description="Maximum characters persisted per Simulation stdout/stderr from Docker probes.",
    )
    recipe_chroma_search_limit_cap: int = Field(
        default=20,
        ge=1,
        le=50,
        description="Upper bound on Chroma hits for GET /recipes/search.",
    )
    recipe_chroma_min_similarity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity (1 - distance) to include in recipe search results.",
    )
    recipe_library_match_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description=(
            "Minimum similarity for ``find_similar_recipes`` / workflow breaker Chrom hints "
            "(cosine mapped as ``1 - distance``)."
        ),
    )
    recipe_chroma_auto_sync_on_verify: bool = Field(
        default=False,
        description=(
            "When true, verified swarm cycles upsert the workflow ``matching_recipe_id`` "
            "embedding into the Recipe Library Chroma collection."
        ),
    )
    recipe_write_sync_chroma: bool = Field(
        default=True,
        description="When true, POST/PATCH /recipes refresh Chroma embeddings after Postgres writes.",
    )
    recipe_catalog_mutations_enabled: bool = Field(
        default=False,
        description=(
            "When false, POST/PATCH/DELETE /recipes return 403. Enable explicitly where operators "
            "manage the Recipe Library (production should pair with an allowlist)."
        ),
    )
    recipe_catalog_mutation_allowlist: list[str] = Field(
        default_factory=list,
        description=(
            "If non-empty, only JWT ``sub`` in this list may POST/PATCH/DELETE recipes "
            "(requires ``recipe_catalog_mutations_enabled``)."
        ),
    )
    recipe_catalog_mutation_required_scope: str | None = Field(
        default=None,
        max_length=128,
        description=(
            "When set, JWT must list this exact scope in a ``scope`` claim "
            "(space-separated OAuth2-style string from ``POST /auth/token``)."
        ),
    )
    recipe_workflow_template_max_json_bytes: int = Field(
        default=262_144,
        ge=4096,
        le=2097152,
        description="Maximum JSON-encoded size for ``workflow_template`` bodies.",
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
    hive_waggle_relay_enabled: bool = Field(
        default=True,
        description="Listen for hive sync cues on Redis waggle and fan them into swarm_events.",
    )

    # --- Security (JWT gates all routes except exempt paths in routers)
    secret_key: str = Field(..., min_length=32, description="HS256 signing secret from env.")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = Field(
        default=7,
        ge=1,
        le=60,
        description="Opaque Redis refresh TTL for dashboard operator sessions.",
    )
    hive_token_client_id: str | None = Field(
        default=None,
        description="HTTP Basic user for POST /api/v1/auth/token (pair with secret).",
    )
    hive_token_client_secret: str | None = Field(
        default=None,
        description="HTTP Basic password (≥32 chars). Leave empty to disable issuance.",
    )
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable Redis sliding-window throttles (burst + sustained) per client IP.",
    )
    rate_limit_burst_max: int = Field(default=10, ge=1, le=10_000)
    rate_limit_burst_window_sec: float = Field(default=1.0, gt=0)
    rate_limit_sustain_max: int = Field(default=100, ge=1, le=200_000)
    rate_limit_sustain_window_sec: float = Field(default=60.0, gt=0)
    health_readiness_cache_sec: float = Field(
        default=3.0,
        ge=0,
        le=120,
        description="TTL (seconds) to coalesce readiness probes; use 0 to disable caching.",
    )
    readiness_require_neo4j: bool = Field(
        default=False,
        description="When true, /health/ready returns 503 if Neo4j heartbeat fails.",
    )
    readiness_require_chroma: bool = Field(
        default=False,
        description="When true, /health/ready returns 503 if ChromaDB heartbeat/list fails.",
    )

    # --- Domain & CORS (Bee-Hive Dashboard origin)
    domain: str = "queenswarm.love"
    cors_origins: list[str] | str = Field(
        default_factory=lambda: [
            "https://queenswarm.love",
            "https://www.queenswarm.love",
            "http://localhost:3000",
        ]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def normalize_cors_origins(cls, value: object) -> list[str]:
        """Allow CSV env strings or JSON lists for dashboard origins."""

        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        if isinstance(value, list):
            cleaned: list[str] = []
            for item in value:
                text = str(item).strip()
                if text:
                    cleaned.append(text)
            return cleaned
        return [
            "https://queenswarm.love",
            "https://www.queenswarm.love",
            "http://localhost:3000",
        ]

    @field_validator("recipe_catalog_mutation_allowlist", mode="before")
    @classmethod
    def normalize_recipe_mutation_allowlist(cls, value: object) -> list[str]:
        """Accept CSV env strings or JSON-ish lists for JWT subject allowlists."""

        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return []

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
    workflow_breaker_tertiary_model: str = Field(
        default="openai/gpt-4o-mini",
        description="Cheap OpenAI route when Grok+Claude fail (requires OPENAI_API_KEY).",
    )
    workflow_breaker_evaluation_model: str = Field(
        default="anthropic/claude-3-5-sonnet-latest",
        description="Evaluator pass — stronger reasoning than primary decomposition models.",
    )
    workflow_breaker_simulation_model: str = Field(
        default="openai/gpt-4o-mini",
        description="Low-cost simulation / roll-forward predictions before guarded execution.",
    )
    workflow_breaker_max_output_tokens: int = 4096
    workflow_breaker_temperature: float = 0.15
    ballroom_guest_ws: bool = Field(
        default=False,
        description="Allow ballroom transcript sockets without JWT (demo kiosks only).",
    )
    hive_dashboard_guest_ws: bool = Field(
        default=False,
        description="Allow /api/v1/ws/live dashboard sockets without JWT (read-only snapshots).",
    )

    @model_validator(mode="after")
    def hive_machine_token_pair_consistency(self) -> Self:
        """Require both hive M2M fields together with minimum secret entropy."""

        cid = self.hive_token_client_id
        secret = self.hive_token_client_secret
        active = bool(cid or secret)
        if active and not (cid and secret):
            msg = (
                "Set both hive_token_client_id and hive_token_client_secret "
                "or omit both (token exchange disabled)."
            )
            raise ValueError(msg)
        if cid is not None and isinstance(cid, str):
            cid_stripped = cid.strip()
            if not cid_stripped:
                msg = "hive_token_client_id cannot be blank whitespace when hive M2M is enabled."
                raise ValueError(msg)
            if isinstance(secret, str) and len(secret) < 32:
                msg = "hive_token_client_secret must be at least 32 characters when enabled."
                raise ValueError(msg)
        return self


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
