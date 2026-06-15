"""Application settings for the Queenswarm bee-hive API (Pydantic v2)."""

from __future__ import annotations

from functools import lru_cache
import socket
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PLUGIN_USER_DIR = _BACKEND_ROOT / "plugins" / "user"


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
    openrouter_api_key: str | None = Field(
        default=None,
        description="Optional OpenRouter key for experimental open-weight agentic models such as Nemotron.",
    )
    deepgram_api_key: str | None = Field(
        default=None,
        description="Optional Deepgram API key for Ballroom STT when provider=deepgram.",
    )
    xai_openai_compatible_base: str = Field(
        default="https://api.x.ai/v1",
        description="Chat Completions-compatible base URL for routing ``xai/`` LiteLLM slugs.",
    )

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
    queenswarm_celery_worker: bool = Field(
        default=False,
        description=(
            "Set true in Celery worker/beat images. Uses per-checkout DB connections so "
            "tasks that call asyncio.run() do not reuse asyncpg connections bound to dead event loops."
        ),
    )
    scaling_mode_enabled: bool = Field(
        default=False,
        description="Enable enterprise horizontal-scaling runtime assumptions and distributed singleton guards.",
    )
    instance_id: str = Field(
        default="",
        description="Stable identifier for this API/worker instance in multi-instance deployments.",
    )
    worker_count: int = Field(
        default=1,
        ge=1,
        le=256,
        description="Expected number of backend worker instances behind load balancer.",
    )
    distributed_lock_ttl_sec: int = Field(
        default=45,
        ge=5,
        le=600,
        description="Redis lease TTL for distributed singleton loops (e.g. relay workers).",
    )
    distributed_lock_renew_interval_sec: float = Field(
        default=15.0,
        gt=1.0,
        le=300.0,
        description="Lease renewal interval for distributed singleton loops.",
    )
    ha_mode_enabled: bool = Field(
        default=False,
        description="Enable high-availability runtime behaviors (drain mode, singleton loops, failover helpers).",
    )
    redis_failover_urls: list[str] | str = Field(
        default_factory=list,
        description="Optional Redis failover endpoints (CSV or list). Tried after REDIS_URL on connection failures.",
    )
    postgres_replica_urls: list[str] | str = Field(
        default_factory=list,
        description="Optional Postgres read-replica DSNs for HA-ready deployments (read paths only).",
    )
    dr_reports_dir: str = Field(
        default="reports/dr",
        description="Directory with dr-drill-*.json/md evidence (env: DR_REPORTS_DIR). Mount read-only in prod.",
    )
    ha_reports_dir: str = Field(
        default="reports/ha",
        description="Directory with ha-chaos-*.json evidence (env: HA_REPORTS_DIR). Mount read-only in prod.",
    )
    codebase_atlas_repo_root: str = Field(
        default="",
        description=(
            "Optional monorepo root for Command Center Codebase Atlas (env: CODEBASE_ATLAS_REPO_ROOT). "
            "Mount host repo read-only in prod (e.g. /repo)."
        ),
    )
    graceful_shutdown_timeout_sec: int = Field(
        default=15,
        ge=1,
        le=300,
        description="Grace period for draining in-flight traffic during shutdown.",
    )
    graceful_shutdown_drain_sec: int = Field(
        default=4,
        ge=0,
        le=120,
        description="Pre-shutdown drain delay before closing dependency clients.",
    )

    # --- Neo4j (knowledge graph, imitation chains, decay)
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str

    # --- ChromaDB (legacy HTTP vectors only when ``VECTOR_STORE_BACKEND=chroma``)
    chroma_host: str = "chromadb"
    chroma_port: int = 8000

    # --- Vector store (PostgreSQL + pgvector default; ``VECTOR_STORE_BACKEND=chroma`` rollback)
    vector_store_backend: Literal["pgvector", "chroma"] = Field(
        default="pgvector",
        description="Hive vector tier: pgvector inside Postgres (default) or legacy Chroma HTTP.",
    )

    plugin_user_dir: str = Field(
        default=str(_DEFAULT_PLUGIN_USER_DIR),
        description="Writable directory scanned for optional operator ``.py`` plugins.",
    )
    allow_user_plugin_uploads: bool = Field(
        default=False,
        description=(
            "Allow runtime upload of user Python plugins via /api/v1/plugins/upload. "
            "Keep false in production unless explicitly operating in trusted admin-only environments."
        ),
    )

    # --- Bee-hive tuning (decentralized sub-swarms → global sync cadence)
    sub_swarm_size: int = Field(
        default=8,
        ge=1,
        description="Default bees per local sub-swarm (scout/eval/sim/action override below).",
    )
    swarm_max_manager_templates_active: int = Field(
        default=3,
        ge=1,
        le=6,
        description="Max dynamic manager template lanes in Ballroom missions and sub-swarm graphs.",
    )
    swarm_max_concurrent_specialist_workers: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Max specialist worker delegations per manager lane in Ballroom missions.",
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
    simulation_docker_memory_mb: int = Field(
        default=256,
        ge=64,
        le=2048,
        description="Per-simulation docker memory cap in MiB when sandbox probe is enabled.",
    )
    simulation_docker_cpu_limit: float = Field(
        default=0.5,
        gt=0.1,
        le=2.0,
        description="Per-simulation docker CPU quota when sandbox probe is enabled.",
    )
    simulation_docker_log_truncate_chars: int = Field(
        default=8192,
        ge=512,
        le=65536,
        description="Maximum characters persisted per Simulation stdout/stderr from Docker probes.",
    )
    simulation_max_parallel: int = Field(
        default=2,
        ge=1,
        le=16,
        description="Maximum in-flight simulation LLM calls per backend process.",
    )
    llm_max_concurrency: int = Field(
        default=6,
        ge=1,
        le=64,
        description="Maximum concurrent LiteLLM completions per backend process.",
    )
    celery_worker_concurrency: int = Field(
        default=3,
        ge=1,
        le=32,
        description="Recommended Celery worker process concurrency for compose/task tuning.",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Process-wide structured log level.",
    )
    log_environment: str = Field(
        default="development",
        description="Static environment label added to each log line (dev/staging/prod).",
    )
    log_service_name: str = Field(
        default="queenswarm-api",
        description="Service name added to structured logs for central aggregators.",
    )
    llm_retry_max_attempts: int = Field(
        default=3,
        ge=1,
        le=8,
        description="Retry budget for transient LLM/provider transport failures.",
    )
    llm_retry_initial_wait_sec: float = Field(
        default=0.35,
        gt=0,
        le=5.0,
        description="Initial retry backoff for LLM/external transient calls.",
    )
    llm_retry_max_wait_sec: float = Field(
        default=4.0,
        gt=0,
        le=30.0,
        description="Maximum retry backoff cap for LLM/external transient calls.",
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
    recipe_hybrid_scoring_enabled: bool = Field(
        default=True,
        description="Blend vector similarity with Postgres imitation graph signals for recipe search.",
    )
    recipe_hybrid_vector_weight: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Weight for vector cosine term in hybrid recipe score.",
    )
    recipe_hybrid_graph_weight: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Weight for imitation/success graph term in hybrid recipe score.",
    )
    recipe_hybrid_neo4j_enabled: bool = Field(
        default=True,
        description="Include Neo4j IMITATED edge counts in hybrid recipe graph signal.",
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
    dreaming_enabled: bool = Field(
        default=True,
        description="Enable nightly Dreamer consolidation cycle in Celery beat.",
    )
    dreaming_cron_hour: int = Field(default=3, ge=0, le=23)
    dreaming_cron_minute: int = Field(default=0, ge=0, le=59)
    dreaming_window_hours: int = Field(default=24, ge=1, le=168)
    dreaming_default_interval_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Default dreaming routine interval when tenant config is unset (hours).",
    )
    dreaming_session_limit: int = Field(
        default=200,
        ge=10,
        le=5000,
        description="Max supervisor sessions scanned per tenant dreaming cycle.",
    )
    dreaming_event_limit: int = Field(
        default=500,
        ge=10,
        le=10_000,
        description="Max supervisor session events scanned per tenant dreaming cycle.",
    )
    episodic_memory_enabled: bool = Field(
        default=True,
        description="Enable explicit episodic memory timeline API (Pattern 8).",
    )
    episodic_memory_retention_days: int = Field(
        default=90,
        ge=7,
        le=365,
        description="Rolling retention window for episodic timeline queries.",
    )
    episodic_memory_timeline_limit: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Default max rows returned by GET /memory/episodic/timeline.",
    )
    dump_sleep_enabled: bool = Field(
        default=True,
        description="Master switch for Dump & Sleep overnight ingest (Phase 4).",
    )
    dump_sleep_upload_root: str = Field(
        default="/tmp/queenswarm-dump-sleep",
        description="Filesystem root for queued Dump & Sleep uploads.",
    )
    dump_sleep_max_files: int = Field(default=20, ge=1, le=100)
    dump_sleep_max_file_bytes: int = Field(default=1_048_576, ge=1024, le=10_485_760)
    dump_sleep_max_content_chars: int = Field(default=120_000, ge=1000, le=500_000)
    dump_sleep_pollen_per_item: float = Field(default=2.5, ge=0.0, le=100.0)
    dump_sleep_report_window_hours: int = Field(default=24, ge=1, le=168)
    free_first_routing_enabled: bool = Field(
        default=True,
        description="Master switch for Free-First / economy LiteLLM routing (Phase 4).",
    )
    local_llm_enabled: bool = Field(
        default=True,
        description="Enable Ollama/vLLM local inference path (Track M LOC1).",
    )
    ollama_api_base: str = Field(
        default="http://127.0.0.1:11434",
        description="Ollama REST base URL for LiteLLM ollama/* models.",
    )
    ollama_default_model: str = Field(
        default="ollama/qwen2.5:7b",
        description="Default LiteLLM slug for local_sovereign routing.",
    )
    vllm_api_base: str = Field(
        default="",
        description="Optional vLLM OpenAI-compatible base (e.g. http://127.0.0.1:8000).",
    )
    vllm_default_model: str = Field(
        default="openai/local-model",
        description="LiteLLM slug paired with vllm_api_base.",
    )
    llm_airgap: bool = Field(
        default=False,
        description="When true, block all cloud LLM hops — local inference only (LOC2).",
    )
    auto_graphify_enabled: bool = Field(
        default=True,
        description="Master switch for Auto-Graphify folder ingest (Phase 4 P1).",
    )
    auto_graphify_upload_root: str = Field(
        default="/tmp/queenswarm-auto-graphify",
        description="Filesystem root for queued Auto-Graphify uploads.",
    )
    auto_graphify_max_files: int = Field(default=40, ge=1, le=200)
    auto_graphify_max_file_bytes: int = Field(default=1_048_576, ge=1024, le=10_485_760)
    auto_graphify_max_content_chars: int = Field(default=120_000, ge=1000, le=500_000)
    auto_graphify_pollen_per_file: float = Field(default=1.5, ge=0.0, le=100.0)
    auto_graphify_report_window_hours: int = Field(default=168, ge=1, le=720)
    output_archive_root: str = Field(
        default="/app/var/outputs",
        description="Filesystem root for final deliverable markdown archives (Outputs lane).",
    )
    output_archive_chroma_enabled: bool = Field(
        default=True,
        description="Embed archived deliverables into Chroma/pgvector when credentials ready.",
    )
    output_archive_embed_max_chars: int = Field(
        default=12_000,
        ge=1000,
        le=500_000,
        description="Max markdown chars embedded per archived deliverable.",
    )
    scout_swarm_size: int = Field(default=8, ge=1)
    eval_swarm_size: int = Field(default=6, ge=1)
    sim_swarm_size: int = Field(default=5, ge=1)
    action_swarm_size: int = Field(default=10, ge=1)
    hive_waggle_relay_enabled: bool = Field(
        default=True,
        description="Listen for hive sync cues on Redis waggle and fan them into swarm_events.",
    )
    hive_mind_enabled: bool = Field(
        default=True,
        description="Enable HiveMind recall pipeline for Ballroom and dashboard routes.",
    )
    hive_mind_max_graph_export_nodes: int = Field(
        default=96,
        ge=16,
        le=500,
        description="Upper bound for /api/v1/hive-mind/graph node snapshots.",
    )
    curated_memory_max_chars: int = Field(
        default=16_000,
        ge=4000,
        le=24_000,
        description=(
            "Max characters per curated memory file (mission/soul/instructions). "
            "16000 is a practical default — enough for rich Instructions without "
            "blowing Queen prompt token budget across all five files."
        ),
    )
    hive_mind_max_query_hits_vector: int = Field(
        default=6,
        ge=1,
        le=64,
        description="Maximum vector hits retrieved for HiveMind prompt/query assembly.",
    )
    hive_mind_graph_cache_ttl_sec: int = Field(
        default=12,
        ge=0,
        le=300,
        description="Short-lived cache for Neo4j graph snapshots on /hive-mind/graph.",
    )
    hive_mind_search_cache_ttl_sec: int = Field(
        default=15,
        ge=0,
        le=300,
        description="Short-lived cache for pgvector/chroma semantic search on /hive-mind/search.",
    )
    hive_mind_chroma_enabled: bool = Field(
        default=True,
        description="Embed and query HiveMind vectors via Chroma/pgvector.",
    )
    hive_mind_vault_root: str = Field(
        default="/app/hive-mind/vault",
        description="Obsidian-compatible Markdown vault root for HiveMind artefacts.",
    )
    hive_mind_embed_max_chars: int = Field(
        default=12_000,
        ge=512,
        le=100_000,
        description="Max characters embedded per deliverable into hive_mind collection.",
    )
    hive_mind_max_graph_neighbor_breadth: int = Field(
        default=6,
        ge=1,
        le=32,
        description="Neo4j neighbour breadth when assembling HiveMind prompt recall.",
    )
    hive_mind_max_prompt_chars: int = Field(
        default=4_000,
        ge=256,
        le=32_000,
        description="Hard cap on HiveMind recall block injected into agent prompts.",
    )
    hive_mind_selective_recall_enabled: bool = Field(
        default=True,
        description="Enable selective graph-neighbour RAG recall mode (Phase 4).",
    )
    hive_mind_default_recall_mode: str = Field(
        default="selective",
        description="Default recall mode when tenant has no override: full | selective.",
    )
    hive_mind_selective_recall_max_hits: int = Field(default=4, ge=1, le=16)
    hive_mind_selective_recall_min_similarity: float = Field(default=0.55, ge=0.0, le=1.0)
    hive_mind_selective_recall_max_chars: int = Field(default=2400, ge=256, le=16_000)
    hive_mind_selective_vault_doc_limit: int = Field(default=3, ge=0, le=8)
    hive_mind_export_max_zip_bytes: int = Field(
        default=25_000_000,
        ge=1_000_000,
        le=200_000_000,
        description="Max in-memory ZIP size for /hive-mind/export bundles.",
    )
    wiki_layer_enabled: bool = Field(
        default=True,
        description="Enable Karpathy-style Wiki Layer (hot wiki + cold raw tier).",
    )
    wiki_layer_max_prompt_chars: int = Field(
        default=4_800,
        ge=512,
        le=16_000,
        description="Max chars for compiled wiki block injected into Queen prompts.",
    )
    wiki_layer_gardener_pollen: float = Field(
        default=3.0,
        ge=0.0,
        le=50.0,
        description="Pollen awarded when Wiki Gardener updates pages.",
    )
    wiki_layer_gardener_sweep_enabled: bool = Field(
        default=True,
        description="Enable periodic Celery Wiki Gardener sweeps (sync raw→wiki every ~5 min).",
    )
    wiki_layer_gardener_interval_sec: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Interval between Wiki Gardener tenant sweeps (seconds).",
    )
    external_integration_audit_to_vault: bool = Field(
        default=True,
        description="Mirror external integration audit lines into HiveMind vault.",
    )

    # --- Security (JWT gates all routes except exempt paths in routers)
    secret_key: str = Field(..., min_length=32, description="HS256 signing secret from env.")
    production_security_mode: bool = Field(
        default=False,
        description="Enable strict production hardening (CSP, CSRF-origin checks, stronger secret requirements).",
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = Field(
        default=90,
        ge=1,
        le=365,
        description="Opaque Redis refresh TTL for dashboard operator sessions.",
    )
    default_tenant_platform_mode: Literal["internal", "commercial"] = Field(
        default="commercial",
        description="Platform mode assigned to new non-admin personal tenants.",
    )
    solo_mode_enabled: bool = Field(
        default=False,
        description=(
            "Solo operator deployment: hide commercial/billing/marketplace UI via platform "
            "feature preset. Code remains for future commercial re-enable."
        ),
    )
    single_admin_mode: bool = Field(
        default=False,
        description=(
            "Strict single-operator deployment mode. Enforces one active admin user + one tenant "
            "at startup and relaxes tenant RBAC checks for the sole operator."
        ),
    )
    single_admin_email: str | None = Field(
        default=None,
        description="Optional keeper admin email used by single-admin cutover tooling.",
    )
    hive_token_client_id: str | None = Field(
        default=None,
        description="HTTP Basic user for POST /api/v1/auth/token (pair with secret).",
    )
    hive_token_client_secret: str | None = Field(
        default=None,
        description="HTTP Basic password (≥32 chars). Leave empty to disable issuance.",
    )
    hive_token_allow_subject_override: bool = Field(
        default=False,
        description=(
            "Allow POST /api/v1/auth/token callers to override JWT subject via request body. "
            "When false, subject is always pinned to the authenticated hive_token_client_id."
        ),
    )
    connector_vault_fernet_key: str | None = Field(
        default=None,
        description=(
            "Optional static Fernet key for connector secret blobs. When empty, "
            "vault crypto derives from SECRET_KEY using HKDF."
        ),
    )
    oauth_public_origin: str = Field(
        default="http://localhost:3000",
        validation_alias=AliasChoices("OAUTH_FRONTEND_PUBLIC_ORIGIN", "OAUTH_PUBLIC_ORIGIN"),
        description="Public cockpit origin for OAuth callback redirects.",
    )
    oauth_redirect_uri: str = Field(
        default="http://localhost:3000/api/auth/callback/connect",
        description="OAuth redirect URI registered at providers.",
    )
    oauth_state_ttl_sec: int = Field(
        default=900,
        ge=60,
        le=7200,
        description="TTL for ephemeral OAuth state blobs stored in Redis.",
    )
    oauth_google_client_id: str = Field(default="")
    oauth_google_client_secret: str = Field(default="")
    oauth_microsoft_client_id: str = Field(default="")
    oauth_microsoft_client_secret: str = Field(default="")
    oauth_github_client_id: str = Field(default="")
    oauth_github_client_secret: str = Field(default="")
    oauth_notion_client_id: str = Field(default="")
    oauth_notion_client_secret: str = Field(default="")
    oauth_meta_client_id: str = Field(default="", description="Meta (Facebook Login) app id for IG/FB social publish.")
    oauth_meta_client_secret: str = Field(default="", description="Meta app secret for IG/FB OAuth consent.")
    oauth_meta_config_id: str = Field(
        default="",
        description=(
            "Facebook Login for Business configuration id (Meta console → Configurations). "
            "Required for Instagram/Business use-case apps when standard dialog/oauth fails."
        ),
    )
    oauth_x_client_id: str = Field(default="", description="X (Twitter) OAuth2 client id for social publish.")
    oauth_x_client_secret: str = Field(default="", description="X (Twitter) OAuth2 client secret for social publish.")
    oauth_tiktok_client_key: str = Field(default="", description="TikTok Login Kit client key for Content Posting API.")
    oauth_tiktok_client_secret: str = Field(default="", description="TikTok client secret for OAuth consent.")
    enable_2fa: bool = Field(
        default=False,
        description="Enable interactive 2FA challenge flow for dashboard login (feature-flag style toggle).",
    )
    dashboard_2fa_session_max_hours: int = Field(
        default=24,
        ge=0,
        le=720,
        description=(
            "Hours after a successful password+TOTP login before refresh tokens are rejected "
            "and full sign-in is required. 0 disables the sliding 2FA window."
        ),
    )
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable Redis sliding-window throttles (burst + sustained) per client IP.",
    )
    rate_limit_user_enabled: bool = Field(
        default=False,
        description="Enable authenticated per-user and per-endpoint throttles.",
    )
    rate_limit_user_sustain_max: int = Field(
        default=480,
        ge=1,
        le=500_000,
        description="Sliding window cap per authenticated subject.",
    )
    rate_limit_user_sustain_window_sec: float = Field(default=60.0, gt=0)
    rate_limit_user_endpoint_max: int = Field(
        default=120,
        ge=1,
        le=500_000,
        description="Sliding window cap per authenticated subject+endpoint tuple.",
    )
    rate_limit_user_endpoint_window_sec: float = Field(default=60.0, gt=0)
    rate_limit_trust_forwarded_headers: bool = Field(
        default=True,
        description=(
            "Trust X-Forwarded-For/X-Real-IP for rate-limit peer resolution. Disable when "
            "the app is directly internet-facing without a trusted reverse proxy."
        ),
    )
    trusted_proxy_hops: int = Field(
        default=1,
        ge=1,
        le=10,
        description=(
            "Number of trusted proxy hops to strip from the right side of X-Forwarded-For "
            "when resolving client IP for rate limiting."
        ),
    )
    rate_limit_burst_max: int = Field(default=10, ge=1, le=10_000)
    rate_limit_burst_window_sec: float = Field(default=1.0, gt=0)
    rate_limit_sustain_max: int = Field(default=100, ge=1, le=200_000)
    rate_limit_sustain_window_sec: float = Field(default=60.0, gt=0)
    rate_limit_agent_run_max: int = Field(
        default=10,
        ge=1,
        le=200_000,
        description="Extra sliding window for POST …/agents/{id}/run (requests per peer IP).",
    )
    rate_limit_agent_run_window_sec: float = Field(default=60.0, gt=0)
    rate_limit_task_create_max: int = Field(
        default=30,
        ge=1,
        le=500_000,
        description="Extra sliding window for POST /api/v1/tasks (requests per peer IP).",
    )
    rate_limit_task_create_window_sec: float = Field(default=60.0, gt=0)
    rate_limit_login_max: int = Field(
        default=20,
        ge=1,
        le=200_000,
        description="Dedicated sliding window for POST /api/v1/auth/login per peer IP.",
    )
    rate_limit_login_window_sec: float = Field(default=300.0, gt=0)
    rate_limit_login_identity_max: int = Field(
        default=8,
        ge=1,
        le=200_000,
        description="Dedicated sliding window for POST /api/v1/auth/login per normalized email identity.",
    )
    rate_limit_login_identity_window_sec: float = Field(default=300.0, gt=0)
    rate_limit_token_exchange_max: int = Field(
        default=30,
        ge=1,
        le=200_000,
        description="Dedicated sliding window for POST /api/v1/auth/token per peer IP.",
    )
    rate_limit_token_exchange_window_sec: float = Field(default=300.0, gt=0)
    health_readiness_cache_sec: float = Field(
        default=3.0,
        ge=0,
        le=120,
        description="TTL (seconds) to coalesce readiness probes; use 0 to disable caching.",
    )
    health_dependency_timeout_sec: float = Field(
        default=2.0,
        gt=0.1,
        le=15.0,
        description="Per-dependency timeout budget for readiness probe checks.",
    )
    readiness_require_neo4j: bool = Field(
        default=False,
        description="When true, /health/ready returns 503 if Neo4j heartbeat fails.",
    )
    readiness_require_chroma: bool = Field(
        default=False,
        description="When true, /health/ready returns 503 if the configured vector tier ping fails.",
    )
    readiness_require_celery: bool = Field(
        default=False,
        description="When true, /health/ready returns 503 if no Celery worker responds to inspect ping.",
    )
    agent_stale_sweep_enabled: bool = Field(
        default=True,
        description="Celery beat task marks RUNNING agents ERROR when last_active_at expires.",
    )
    dynamic_agent_scheduler_enabled: bool = Field(
        default=True,
        description="Enable periodic dynamic agent scheduler tick (enqueue due AgentConfig runs).",
    )
    recipe_warmup_enabled: bool = Field(
        default=True,
        description="Enable nightly recipe warmup beat task.",
    )
    manager_peer_review_enabled: bool = Field(
        default=True,
        description="Enable periodic manager peer-review sweep beat task.",
    )
    pollen_reroster_enabled: bool = Field(
        default=True,
        description="Enable daily pollen re-roster advisory beat task.",
    )
    agent_stale_timeout_sec: int = Field(
        default=600,
        ge=60,
        le=86400,
        description="Seconds without last_active_at before a RUNNING agent is marked stale.",
    )

    # --- Domain & CORS (Bee-Hive Dashboard origin)
    domain: str = "queenswarm.love"
    dashboard_totpissuer: str = Field(
        default="Queenswarm",
        min_length=1,
        max_length=80,
        description="Issuer embedded in otpauth:// URIs for dashboard TOTP (Authenticator label).",
    )
    cors_origins: list[str] | str = Field(
        default_factory=lambda: [
            "https://queenswarm.love",
            "https://www.queenswarm.love",
            "http://localhost:3000",
        ]
    )

    @field_validator("vector_store_backend", mode="before")
    @classmethod
    def coerce_vector_store_backend(cls, value: object) -> str:
        """Map deprecated ``qdrant`` env values to pgvector."""

        raw = str(value or "pgvector").strip().lower()
        if raw in ("qdrant", "qdr", "postgres", "pg"):
            return "pgvector"
        if raw == "chroma":
            return "chroma"
        if raw == "pgvector":
            return "pgvector"
        return "pgvector"

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

    @field_validator("redis_failover_urls", "postgres_replica_urls", mode="before")
    @classmethod
    def normalize_optional_url_lists(cls, value: object) -> list[str]:
        """Accept CSV env strings or lists for optional HA endpoint lists."""

        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        if isinstance(value, list):
            out: list[str] = []
            for item in value:
                text = str(item).strip()
                if text:
                    out.append(text)
            return out
        return []

    @field_validator("instance_id", mode="before")
    @classmethod
    def normalize_instance_id(cls, value: object) -> str:
        """Normalize instance identifier and fall back to hostname-derived id."""

        text = str(value or "").strip()
        if text:
            return text
        host = socket.gethostname().strip() or "unknown"
        safe = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "-" for ch in host)
        return f"api-{safe[:64]}"

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
    slack_harness_trainer_enabled: bool = Field(
        default=True,
        description="Enable Slack slash-command + dashboard feedback → behavioral INSTRUCTIONS memory.",
    )
    slack_harness_trainer_signing_secret: str = Field(
        default="",
        description="Slack app signing secret for /harness/slack-trainer/slack-command verification.",
    )
    slack_harness_trainer_tenant_id: str | None = Field(
        default=None,
        description="Tenant UUID receiving Slack slash-command feedback (required for Slack ingress).",
    )
    notify_email: str | None = Field(
        default=None,
        description="Default recipient for SMTP alerts when ``notify_email`` is not passed explicitly.",
    )
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
    workflow_breaker_primary_model: str = Field(
        default="xai/grok-3-mini",
        description="LiteLLM slug for primary decomposition (xAI Grok).",
    )
    workflow_breaker_fallback_model: str = Field(
        default="anthropic/claude-haiku-4-5-20251001",
        description="Claude Haiku 4.5 fallback when Grok primary errors (403, auth, etc.).",
    )
    workflow_breaker_tertiary_model: str = Field(
        default="openai/gpt-4o-mini",
        description="Cheap OpenAI route when Grok+Claude fail (requires OPENAI_API_KEY).",
    )
    workflow_breaker_evaluation_model: str = Field(
        default="anthropic/claude-haiku-4-5-20251001",
        description="Evaluator pass — aligned with Claude fallback stack.",
    )
    workflow_breaker_simulation_model: str = Field(
        default="openai/gpt-4o-mini",
        description="Low-cost simulation / roll-forward predictions before guarded execution.",
    )
    workflow_breaker_max_output_tokens: int = 4096
    workflow_breaker_temperature: float = 0.15
    factory_llm_smoke_timeout_sec: float = Field(
        default=45.0,
        gt=5.0,
        le=120.0,
        description="Max seconds for Factory LLM smoke ping before failing fast in UI.",
    )
    ballroom_guest_ws: bool = Field(
        default=False,
        description="Allow ballroom transcript sockets without JWT (demo kiosks only).",
    )
    ballroom_capsule_backend: Literal["redis", "memory"] = Field(
        default="redis",
        description="Persist ballroom session capsules in Redis (multi-worker) or in-process memory (tests).",
    )
    ballroom_capsule_ttl_sec: int = Field(
        default=86_400,
        ge=60,
        description="TTL for ballroom capsule JSON in Redis (seconds); ignored for memory backend.",
    )
    hive_ballroom_post_mortem_enabled: bool = Field(
        default=True,
        description="Persist post-mortem reflection + recipe autosave after Ballroom seven-step missions.",
    )
    voice_enabled: bool = Field(
        default=False,
        description="Enable voice + multimodal pipeline (STT/TTS) for ballroom and agent control flows.",
    )
    ballroom_fast_model: str = Field(
        default="grok-4-fast-non-reasoning",
        description="Direct xAI model for latency_mode=fast Ballroom orchestrator replies (~sub-second).",
    )
    ballroom_fast_max_tokens: int = Field(default=64, ge=16, le=256)
    ballroom_fast_temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    ballroom_voice_live_model: str = Field(
        default="grok-voice-latest",
        description="xAI Voice Agent model for continuous Ballroom voice calls.",
    )
    ballroom_voice_live_token_ttl_sec: int = Field(default=300, ge=60, le=900)
    voice_stt_model: str = Field(
        default="whisper-1",
        description="OpenAI Whisper-compatible model slug used for STT.",
    )
    voice_tts_model: str = Field(
        default="eleven_multilingual_v2",
        description="ElevenLabs model id for text-to-speech when ELEVENLABS_API_KEY is configured.",
    )
    elevenlabs_api_key: str | None = Field(
        default=None,
        description="Optional ElevenLabs API key for high-fidelity TTS voice output.",
    )
    elevenlabs_voice_id: str = Field(
        default="21m00Tcm4TlvDq8ikWAM",
        description="Default ElevenLabs voice id for generated speech responses.",
    )
    voice_tts_model_openai: str = Field(
        default="gpt-4o-mini-tts",
        description="Fallback OpenAI TTS model when ElevenLabs is not configured.",
    )
    voice_tts_openai_voice: str = Field(
        default="alloy",
        description="OpenAI voice preset for fallback TTS.",
    )
    voice_tts_xai_voice_id: str = Field(
        default="Ara",
        description="Default xAI Grok TTS voice id when operator preference is auto.",
    )
    voice_tts_xai_language: str = Field(
        default="en",
        description="Default xAI Grok TTS language code (ISO 639-1).",
    )
    voice_tts_xai_optimize_streaming_latency: int = Field(
        default=0,
        ge=0,
        le=4,
        description="xAI TTS optimize_streaming_latency hint (0–4); fast mode forces 1.",
    )
    voice_tts_xai_output_codec: str = Field(
        default="",
        description="Optional xAI TTS output codec (e.g. mp3). Empty skips output_format block.",
    )
    voice_tts_xai_sample_rate: int = Field(
        default=24_000,
        ge=8_000,
        le=48_000,
        description="xAI TTS sample rate when output_format is sent.",
    )
    voice_tts_xai_bit_rate: int = Field(
        default=128_000,
        ge=32_000,
        le=320_000,
        description="xAI TTS bit rate when output_format is sent.",
    )
    hive_dashboard_guest_ws: bool = Field(
        default=False,
        description="Allow /api/v1/ws/live dashboard sockets without JWT (read-only snapshots).",
    )
    advanced_monitoring_enabled: bool = Field(
        default=False,
        description="Expose advanced monitoring snapshots/routes for operators.",
    )
    enterprise_monitoring_enabled: bool = Field(
        default=False,
        description="Enable enterprise-only monitoring/observability extensions (admin + enterprise tier gates).",
    )
    opentelemetry_enabled: bool = Field(
        default=False,
        description="Enable OpenTelemetry-ready trace context propagation labels and headers.",
    )
    opentelemetry_service_name: str = Field(
        default="queenswarm-api",
        description="Service name advertised in OTel-ready tracing metadata.",
    )
    opentelemetry_exporter_otlp_endpoint: str = Field(
        default="",
        description="Optional OTLP endpoint for external tracing collector integration.",
    )
    langfuse_enabled: bool = Field(
        default=False,
        description="Emit LiteLLM traces to LangFuse via success/failure callbacks.",
    )
    langfuse_public_key: str = Field(
        default="",
        description="LangFuse public key (LANGFUSE_PUBLIC_KEY).",
    )
    langfuse_secret_key: str = Field(
        default="",
        description="LangFuse secret key (LANGFUSE_SECRET_KEY).",
    )
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com",
        description="LangFuse API host (self-hosted or cloud).",
    )
    pending_review_enabled: bool = Field(
        default=True,
        description="Hold sub-threshold confidence outcomes in operator pending-review queue.",
    )
    pending_review_confidence_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Outcomes below this simulator confidence fraction require human approval.",
    )
    pending_review_notify_slack: bool = Field(
        default=True,
        description="Best-effort Slack ping when a pending review item is enqueued.",
    )
    alerting_enabled: bool = Field(
        default=False,
        description="Enable enterprise alert dispatch to Slack/email/PagerDuty channels.",
    )
    alert_memory_percent_threshold: float = Field(
        default=88.0,
        ge=1.0,
        le=100.0,
        description="Host memory threshold for high-memory alerts.",
    )
    alert_supervisor_failures_threshold: int = Field(
        default=1,
        ge=1,
        le=1000,
        description="Minimum supervisor failures in 24h to trigger critical alert.",
    )
    alert_rate_limit_blocks_5m_threshold: int = Field(
        default=40,
        ge=1,
        le=500000,
        description="Rate-limit block threshold in 5-minute window for alerting.",
    )
    alert_scaling_events_5m_threshold: int = Field(
        default=5,
        ge=1,
        le=500000,
        description="Scaling event threshold in 5-minute window for alerting.",
    )
    alert_dispatch_cooldown_sec: int = Field(
        default=300,
        ge=30,
        le=86400,
        description="Minimum cooldown between repeated external alert dispatches for same code.",
    )
    pagerduty_routing_key: str = Field(
        default="",
        description="PagerDuty Events API v2 routing key for enterprise alert delivery.",
    )
    pagerduty_events_api_url: str = Field(
        default="https://events.pagerduty.com/v2/enqueue",
        description="PagerDuty events endpoint override for enterprise environments.",
    )
    simulations_enabled: bool = Field(
        default=True,
        description="Expose simulations ledger routes in operator API.",
    )
    leaderboard_enabled: bool = Field(
        default=False,
        description="Expose leaderboard-style learning/ranking API surfaces.",
    )
    verified_pollen_leaderboard_enabled: bool = Field(
        default=True,
        description="Maintain Redis ZSET leaderboard for simulation-verified pollen rewards.",
    )
    verified_pollen_leaderboard_ttl_sec: int = Field(
        default=86_400 * 30,
        ge=3600,
        description="TTL refresh for verified pollen leaderboard Redis keys.",
    )
    skill_export_premium_enabled: bool = Field(
        default=True,
        description="Require purchase or Pro tier before exporting verified premium skills.",
    )
    skill_export_premium_price_eur_cents: int = Field(
        default=1900,
        ge=100,
        description="Default one-time premium price for verified skill export (EUR cents).",
    )
    skill_marketplace_ugc_enabled: bool = Field(
        default=True,
        description="Allow tenants to submit verified recipes for curator marketplace review.",
    )
    skill_marketplace_platform_cut_bps: int = Field(
        default=2500,
        ge=2000,
        le=3000,
        description="Platform revenue share on UGC skill sales (basis points, default 25%).",
    )
    ugc_content_engine_enabled: bool = Field(
        default=True,
        description="Enable lead magnet landing pages and share-card generation.",
    )
    bee_gamification_enabled: bool = Field(
        default=True,
        description="Enable verified-workflow badge profiles and gamification UI.",
    )
    enterprise_workspace_enabled: bool = Field(
        default=True,
        description="Enable white-label branding and enterprise compliance workspace UI.",
    )
    skill_publish_github_org: str = Field(
        default="queenswarm",
        description="GitHub org for public skills repo publish hints.",
    )
    skill_publish_github_repo: str = Field(
        default="skills",
        description="GitHub repo name for skill folder publish hints.",
    )
    paper_trading_enabled: bool = Field(
        default=False,
        description="Deprecated — paper trading removed; keep false.",
    )
    hourly_youtube_crypto_roll_enabled: bool = Field(
        default=True,
        description="Enable hourly YouTube/crypto background roll Celery task.",
    )
    paper_trading_tick_interval_sec: int = Field(
        default=900,
        ge=60,
        le=86_400,
        description="Celery beat interval for paper trading ticks (default 15 min).",
    )
    paper_trading_default_cash_usd: float = Field(
        default=10_000.0,
        ge=100.0,
        description="Starting simulated cash for new paper accounts.",
    )
    paper_trading_confidence_threshold: float = Field(
        default=0.8,
        ge=0.5,
        le=1.0,
        description="Minimum signal confidence before paper execution.",
    )
    paper_trading_fee_bps: float = Field(
        default=10.0,
        ge=0.0,
        le=100.0,
        description="Simulated taker fee in basis points.",
    )
    recipes_enabled: bool = Field(
        default=False,
        description="Expose recipe catalog/search/autosave routes.",
    )
    security_2fa_advanced_enabled: bool = Field(
        default=False,
        description="Enable advanced 2FA management endpoints beyond baseline login verification.",
    )
    api_key_management_enabled: bool = Field(
        default=False,
        description="Enable scripted dashboard API key management endpoints.",
    )
    phase70_consolidated_nav_enabled: bool = Field(
        default=True,
        description="Frontend/client hint for consolidated navigation rollout.",
    )
    oauth_callback_rate_per_ip: int = Field(
        default=30,
        ge=1,
        le=10000,
        description="Rate limit for OAuth callback completion attempts per IP.",
    )
    oauth_callback_rate_window_sec: float = Field(
        default=60.0,
        gt=0,
        le=3600,
        description="Window for OAuth callback per-IP limiter.",
    )
    dynamic_connector_registry_cache_ttl_sec: int = Field(
        default=300,
        ge=30,
        le=3600,
        description="Redis snapshot TTL for active dynamic connector manifests.",
    )
    dynamic_connector_rate_limit_per_minute: int = Field(
        default=120,
        ge=1,
        le=5000,
        description="Connector-level outbound invoke budget per minute.",
    )
    dynamic_connector_tool_rate_limit_per_minute: int = Field(
        default=60,
        ge=1,
        le=5000,
        description="Per-tool outbound invoke budget per minute (security/abuse guardrail).",
    )
    dynamic_connector_circuit_failure_threshold: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Consecutive failure threshold before opening connector circuit breaker.",
    )
    dynamic_connector_circuit_open_sec: float = Field(
        default=90.0,
        gt=1.0,
        le=3600.0,
        description="Seconds circuit remains open after repeated connector failures.",
    )
    dynamic_connector_tool_timeout_ms: int = Field(
        default=2500,
        ge=100,
        le=120000,
        description="Timeout budget for one dynamic connector tool HTTP invoke.",
    )
    grokipedia_base_url: str = Field(
        default="",
        description="Optional override base URL for built-in grokipedia connector route.",
    )
    phase3_obsidian_watch_enabled: bool = Field(
        default=False,
        description="Enable periodic Obsidian vault watch/sync loop for HiveMind ingestion.",
    )
    phase3_obsidian_poll_interval_sec: int = Field(
        default=300,
        ge=30,
        le=3600,
        description="Polling interval for Obsidian watch mode.",
    )
    phase3_obsidian_max_files_per_sync: int = Field(
        default=50,
        ge=1,
        le=5000,
        description="Maximum Obsidian markdown files ingested during one sync pass.",
    )
    supervisor_dynamic_subagents_enabled: bool = Field(
        default=False,
        description="Enable dynamic supervisor sessions + sub-agent orchestration APIs.",
    )
    supervisor_durable_mode_enabled: bool = Field(
        default=False,
        description="Allow durable Celery-backed execution mode for supervisor sub-agent runs.",
    )
    supervisor_default_runtime_mode: Literal["inprocess", "durable"] = Field(
        default="inprocess",
        description="Default runtime mode when API requests omit explicit supervisor mode.",
    )
    supervisor_event_log_limit: int = Field(
        default=500,
        ge=50,
        le=5000,
        description="Maximum events returned per supervisor session timeline request.",
    )
    supervisor_skills_enabled: bool = Field(
        default=False,
        description="Enable lightweight Markdown skills injection for supervisor/sub-agent prompts.",
    )
    supervisor_sub_agent_llm_enabled: bool = Field(
        default=True,
        description="When true, supervisor sub-agents call LiteLLM + tools instead of harness stub steps.",
    )
    supervisor_max_skills_per_agent: int = Field(
        default=5,
        ge=1,
        le=16,
        description="Maximum number of skills selected per supervisor sub-agent.",
    )
    skill_lazy_reference_fetch_enabled: bool = Field(
        default=True,
        description="Fetch skill reference pointers (URLs/docs) on demand instead of inlining full bodies.",
    )
    skill_reference_fetch_max_chars: int = Field(
        default=3000,
        ge=256,
        le=12000,
        description="Max characters loaded per skill reference fetch.",
    )
    tracer_bullet_kanban_enabled: bool = Field(
        default=True,
        description="Enable tracer bullet workflow → Kanban vertical slice materialization.",
    )
    tracer_bullet_kanban_auto_on_intake: bool = Field(
        default=True,
        description="Auto-create Kanban slices when operator intake_task runs workflow breaker.",
    )
    lsp_mcp_bridge_enabled: bool = Field(
        default=False,
        description="Expose lightweight symbol index as MCP tools + prompt context for coder sub-agents.",
    )
    lsp_mcp_bridge_max_results: int = Field(
        default=12,
        ge=1,
        le=50,
        description="Max symbol matches or references returned per LSP bridge call.",
    )
    lsp_mcp_bridge_max_file_bytes: int = Field(
        default=512_000,
        ge=4096,
        le=2_000_000,
        description="Skip indexing files larger than this many bytes.",
    )
    rubric_templates_enabled: bool = Field(
        default=True,
        description="Expose curated subjective scoring rubrics in harness + workflow evaluation.",
    )
    forager_intelligence_loop_enabled: bool = Field(
        default=False,
        description="Schedule daily read-only Forager Intelligence Loop scan via Celery beat.",
    )
    forager_intelligence_cron_hour: int = Field(
        default=6,
        ge=0,
        le=23,
        description="UTC hour for daily Forager Intelligence Loop Celery beat tick.",
    )
    forager_intelligence_cron_minute: int = Field(
        default=0,
        ge=0,
        le=59,
        description="UTC minute for daily Forager Intelligence Loop Celery beat tick.",
    )
    social_intel_scrape_enabled: bool = Field(
        default=True,
        description="Schedule periodic YouTube/X forager scrape + HiveMind ingest via Celery beat.",
    )
    social_intel_tick_interval_hours: int = Field(
        default=4,
        ge=1,
        le=24,
        description="Hours between social intel forager scrape ticks (YouTube + X delta ingest).",
    )
    social_intel_cron_hour: int = Field(
        default=7,
        ge=0,
        le=23,
        description="Legacy UTC hour anchor when social_intel_tick_interval_hours is unset (deprecated).",
    )
    social_intel_cron_minute: int = Field(
        default=30,
        ge=0,
        le=59,
        description="UTC minute for daily social intel forager scrape tick.",
    )
    self_extending_tool_marketplace_enabled: bool = Field(
        default=True,
        description="Forager intelligence scan → one-click MCP preset install via harness apply.",
    )
    execution_studio_enabled: bool = Field(
        default=True,
        description="Execution Studio product layer — governed external app connections and tool execution.",
    )
    publish_queue_enabled: bool = Field(
        default=True,
        description="Publish Queue Phase B — operator approval inbox for verified publish packs (simulate-only).",
    )
    morning_publish_pipeline_enabled: bool = Field(
        default=True,
        description="Phase D — Life OS brief → content draft → critic verify → Publish Queue timeline.",
    )
    social_publish_enabled: bool = Field(
        default=True,
        description="Phase C — social channel publish adapter (Instagram, Facebook, X, TikTok).",
    )
    social_publish_live_enabled: bool = Field(
        default=False,
        description="Allow live upstream social API calls — default false until OAuth + operator ready.",
    )
    publish_queue_telegram_notify_enabled: bool = Field(
        default=True,
        description="Phase E — Telegram ping when operator approves a publish pack (if bot configured).",
    )
    social_publish_telegram_notify_on_auto_live_enabled: bool = Field(
        default=True,
        description="Phase G — Telegram ping when trusted auto-live succeeds (if bot configured).",
    )
    scheduled_publish_enabled: bool = Field(
        default=True,
        description="Phase E — Celery tick runs simulate publish for approved packs past scheduled_at.",
    )
    social_publish_rate_limit_enabled: bool = Field(
        default=True,
        description="Redis sliding-window limits for live social publish (per channel + global).",
    )
    social_publish_rate_limit_fail_closed: bool = Field(
        default=True,
        description="Block live publish when Redis rate limiter is unavailable.",
    )
    social_publish_live_daily_max_per_channel: int = Field(
        default=10,
        ge=1,
        le=500,
        description="Max live publishes per channel per operator per rate window.",
    )
    social_publish_live_daily_max_global: int = Field(
        default=30,
        ge=1,
        le=2000,
        description="Max live publishes across all channels per operator per rate window.",
    )
    commerce_webhooks_enabled: bool = Field(
        default=False,
        description="Enable /commerce/webhooks/stripe ingress for e-shop order/payment events.",
    )
    stripe_webhook_secret: str = Field(
        default="",
        description="Stripe webhook signing secret (whsec_...) — never log or expose.",
    )
    gumroad_webhook_secret: str = Field(
        default="",
        description="Path secret for POST /commerce/webhooks/gumroad/{secret} Gumroad ping ingress.",
    )
    gumroad_purchase_unlock_enabled: bool = Field(
        default=True,
        description="When true, Gumroad sale ping unlocks premium recipe export for matching dashboard email.",
    )
    gumroad_post_purchase_onboarding_enabled: bool = Field(
        default=True,
        description="Send REV1 post-purchase onboarding email + simulate proof JSON on Gumroad sale ping.",
    )
    marketing_public_origin: str = Field(
        default="https://letagentscook.org",
        description="Public marketing site origin for buyer onboarding links (REV1).",
    )
    marketing_public_eval_enabled: bool = Field(
        default=True,
        description="Enable public Eval-as-a-Service on POST /marketing/eval (REV2).",
    )
    marketing_public_eval_rate_limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Max free eval requests per IP per window (REV2).",
    )
    marketing_public_eval_rate_window_sec: float = Field(
        default=3600.0,
        gt=0,
        description="Sliding window seconds for public eval rate limit.",
    )
    social_publish_rate_limit_window_sec: float = Field(
        default=86400.0,
        gt=0,
        description="Sliding window for live publish rate limits (default 24h).",
    )
    social_publish_trusted_auto_enabled: bool = Field(
        default=False,
        description="Phase G — allow tenant auto-live when channel mode=auto and simulate history meets threshold.",
    )
    social_publish_trusted_auto_min_simulates: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Min successful social simulates per channel before auto-live is allowed.",
    )
    tiktok_publish_status_poll_enabled: bool = Field(
        default=True,
        description="Poll TikTok publish_status_fetch after successful video_publish_init (live).",
    )
    tiktok_publish_status_poll_max_attempts: int = Field(
        default=6,
        ge=1,
        le=30,
        description="Max poll attempts after TikTok video_publish_init.",
    )
    tiktok_publish_status_poll_interval_sec: float = Field(
        default=2.0,
        ge=0.5,
        le=30.0,
        description="Seconds between TikTok publish status polls.",
    )
    publish_pack_venice_media_hook_enabled: bool = Field(
        default=False,
        description="Server-side Venice image_generate when publish pack lacks media_url (Instagram/FB).",
    )
    publish_pack_monid_video_hook_enabled: bool = Field(
        default=False,
        description="Server-side Monid video resolve when TikTok pack lacks media_url.",
    )
    prediction_markets_enabled: bool = Field(
        default=True,
        description="Enable Polymarket marketplace connectors for trading bot lanes.",
    )
    prediction_markets_live_trading_enabled: bool = Field(
        default=False,
        description="Allow live order placement on prediction markets — default simulate until operator ready.",
    )
    prediction_markets_max_order_usd: float = Field(
        default=2_500.0,
        ge=1.0,
        le=500_000.0,
        description="Default max notional USD per live prediction-market order.",
    )
    prediction_markets_live_daily_max_per_venue: int = Field(
        default=20,
        ge=1,
        le=500,
        description="Max live orders per venue per operator per rate window.",
    )
    prediction_markets_live_daily_max_global: int = Field(
        default=50,
        ge=1,
        le=2000,
        description="Max live prediction-market orders across venues per operator per window.",
    )
    prediction_markets_rate_limit_window_sec: float = Field(
        default=86400.0,
        gt=0,
        description="Sliding window for live prediction-market order rate limits.",
    )
    prediction_markets_rate_limit_fail_closed: bool = Field(
        default=True,
        description="Block live orders when Redis rate limiter unavailable.",
    )
    trading_cockpit_enabled: bool = Field(
        default=True,
        description="Trading Cockpit panel — paper + real prediction-market agent control in Execution Studio.",
    )
    trading_cockpit_telegram_notify_on_fill: bool = Field(
        default=True,
        description="Notify operator Telegram channel on paper fill or live trade audit (when configured).",
    )
    operator_loop_enabled: bool = Field(
        default=True,
        description="Unified Operator Loop snapshot — overnight + brief + publish + trading.",
    )
    operator_loop_telegram_morning_enabled: bool = Field(
        default=True,
        description="07:30 UTC Telegram morning digest from Operator Loop (when Telegram configured).",
    )
    operator_control_plane_enabled: bool = Field(
        default=True,
        description="Unified Operator Control Plane — /operator/cockpit compose + act router.",
    )
    business_background_team_enabled: bool = Field(
        default=False,
        description="BA3 — snapshot-only heartbeat bees (marketing/revenue/factory ops). No LLM.",
    )
    proactive_pulse_enabled: bool = Field(
        default=True,
        description="BA5 — proactive midday pulse (what changed / what ran autonomously).",
    )
    proactive_pulse_telegram_midday_enabled: bool = Field(
        default=False,
        description="12:00 UTC Telegram midday pulse when Telegram configured.",
    )
    business_cross_lane_learning_enabled: bool = Field(
        default=True,
        description="BA7 — cross-lane recipe suggestions in CBO (semantic search, no LLM).",
    )
    calendar_daily_planner_enabled: bool = Field(
        default=True,
        description="PA2 — Google Calendar events in solo daily plan (read-only connector).",
    )
    knowledge_elicitation_enabled: bool = Field(
        default=True,
        description="OBS2 — Brain Pack gap prompts in Knowledge UI.",
    )
    stakeholder_grill_wizard_enabled: bool = Field(
        default=True,
        description="NP1 — Stakeholder Grill wizard on Mission Kanban (structured brief artifact).",
    )
    trading_thesis_wizard_enabled: bool = Field(
        default=True,
        description="NP5 — Trading thesis brief wizard on Trading cockpit (risk preflight artifact).",
    )
    loop_guardrails_enabled: bool = Field(
        default=True,
        description="LOOP2 — Closed-loop guardrails (max turns, min score, cost cap) on supervisor sessions.",
    )
    loop_guardrails_default_max_turns: int = Field(
        default=5,
        ge=1,
        le=25,
        description="LOOP2 — default max sub-agent turns per closed loop.",
    )
    loop_guardrails_default_min_score: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="LOOP2 — default minimum rubric score (0–1, 0.8 = 4/5).",
    )
    loop_guardrails_default_cost_cap_usd: float = Field(
        default=0.50,
        ge=0.05,
        le=50.0,
        description="LOOP2 — default per-session LLM spend cap (USD).",
    )
    loop_guardrails_default_cost_warn_ratio: float = Field(
        default=0.60,
        ge=0.1,
        le=1.0,
        description="LOOP2 — fraction of cost cap that triggers warn state.",
    )
    factory_queue_slo_enabled: bool = Field(
        default=True,
        description="TR4 — Skill Factory queue SLO panel in factory snapshot.",
    )
    factory_queue_slo_awaiting_forge_warn: int = Field(
        default=3,
        ge=1,
        le=50,
        description="TR4 — awaiting_forge count that triggers warn status.",
    )
    factory_queue_slo_awaiting_forge_critical: int = Field(
        default=8,
        ge=2,
        le=100,
        description="TR4 — awaiting_forge count that triggers critical status.",
    )
    factory_queue_slo_critic_rate_warn: float = Field(
        default=0.65,
        ge=0.1,
        le=1.0,
        description="TR4 — critic approval rate floor (0–1) below which SLO warns.",
    )
    factory_queue_slo_weekly_cap_warn_pct: float = Field(
        default=0.85,
        ge=0.5,
        le=1.0,
        description="TR4 — weekly build cap usage ratio (0–1) that triggers warn.",
    )
    grok_control_plane_enabled: bool = Field(
        default=True,
        description="Enable Grok Control Plane in cockpit (plan/approve/execute).",
    )
    grok_cp_cli_enabled: bool = Field(
        default=True,
        description="Allow worker to call Grok CLI for plan generation.",
    )
    grok_cp_execute_commands: bool = Field(
        default=False,
        description="Allow worker to execute approved command profiles.",
    )
    grok_cp_cli_binary: str = Field(
        default="grok",
        description="Binary name/path for Grok CLI bridge.",
    )
    grok_cp_repo_root: str = Field(
        default="/app",
        description="Repository root for command execution in Grok runs.",
    )
    grok_cp_command_timeout_sec: int = Field(
        default=240,
        ge=30,
        le=3600,
        description="Per-command timeout for Grok Control Plane worker execution.",
    )
    grok_cp_failed_alert_threshold: int = Field(
        default=3,
        ge=1,
        le=100,
        description="Failed run count threshold for Grok health warning/escalation badges.",
    )
    grok_cp_allow_prod_deploy: bool = Field(
        default=False,
        description="Allow prod_deploy run mode in Grok Control Plane.",
    )
    grok_cp_require_approval_for_risk: str = Field(
        default="medium,high,critical",
        description="Comma-separated risk levels that require explicit operator approval.",
    )
    grok_cp_deny_command_patterns: str = Field(
        default="rm -rf,shutdown,reboot,:(){:|:&};:,mkfs,dd if=,curl | sh",
        description="Comma-separated forbidden shell snippets for Grok run commands.",
    )
    grok_cp_profile_read_only_commands: str = Field(
        default="git status --short,git diff --stat",
        description="Comma-separated allowlisted read-only command profile.",
    )
    grok_cp_profile_ci_quick_commands: str = Field(
        default="git status --short,./scripts/ci-local.sh --quick",
        description="Comma-separated allowlisted quick CI profile commands.",
    )
    grok_cp_profile_deploy_candidate_commands: str = Field(
        default="git status --short,./scripts/validate-prod-env.sh",
        description="Comma-separated allowlisted deploy-candidate profile commands.",
    )
    grok_cp_profile_prod_deploy_commands: str = Field(
        default="git status --short,./scripts/deploy-prod.sh --dry-run",
        description="Comma-separated allowlisted prod-deploy profile commands.",
    )
    grok_cp_dedup_hard_gate_enabled: bool = Field(
        default=True,
        description="Block new Grok run creation on high dedup overlap unless force override is set.",
    )
    grok_cp_dedup_reuse_threshold: float = Field(
        default=0.62,
        ge=0.05,
        le=0.98,
        description="Dedup score threshold above which recommendation is reuse and hard gate may block.",
    )
    grok_cp_dedup_hybrid_threshold: float = Field(
        default=0.35,
        ge=0.01,
        le=0.95,
        description="Dedup score threshold above which recommendation is hybrid.",
    )
    grok_cp_dedup_min_score_by_source: str = Field(
        default="task:0.12,recipe:0.18,knowledge:0.16,grok_run:0.2",
        description="Per-source minimal dedup score filter as source:threshold CSV.",
    )
    grok_cp_dedup_weight_by_source: str = Field(
        default="task:1.0,recipe:1.1,knowledge:0.95,grok_run:1.15",
        description="Per-source score weight multiplier as source:weight CSV.",
    )
    grok_cp_hivemind_review_alert_threshold: int = Field(
        default=10,
        ge=1,
        le=200,
        description="Pending low-confidence Grok HiveMind queue size threshold for operator escalation alerts.",
    )
    grok_cp_hivemind_review_alert_cooldown_sec: int = Field(
        default=900,
        ge=60,
        le=86400,
        description="Cooldown window between repeated Grok HiveMind review queue alerts.",
    )
    grok_cp_hivemind_review_alert_max_age_hours: int = Field(
        default=24,
        ge=1,
        le=240,
        description="Oldest pending low-confidence Grok HiveMind item age threshold (hours) for escalation.",
    )
    grok_cp_cost_cap_usd_24h: float = Field(
        default=25.0,
        ge=0.0,
        le=100000.0,
        description="Soft budget cap for estimated Grok execution cost over last 24h.",
    )
    grok_cp_estimated_cost_per_run: str = Field(
        default="read_only:0.03,code_edit:0.12,code_edit_and_test:0.30,deploy_candidate:0.55,prod_deploy:0.80",
        description="Per-run estimated cost map as run_mode:usd CSV for governance dashboard.",
    )
    grok_cp_timeout_alert_threshold_24h: int = Field(
        default=3,
        ge=1,
        le=200,
        description="Timeout breach threshold (exit code 124) in last 24h for governance escalation badge.",
    )
    grok_cp_risk_escalation_threshold_24h: int = Field(
        default=6,
        ge=1,
        le=200,
        description="High+critical Grok run count threshold in last 24h for governance escalation badge.",
    )
    grok_cp_escalation_dedup_enabled: bool = Field(
        default=True,
        description="Enable backend-side cooldown dedup gate for escalation runs.",
    )
    grok_cp_escalation_cooldown_sec: int = Field(
        default=600,
        ge=30,
        le=86400,
        description="Cooldown window for identical escalation_kind run creation.",
    )
    grok_cp_last_resumed_marker_ttl_hours: int = Field(
        default=24,
        ge=1,
        le=720,
        description="TTL window for showing persisted last resumed escalation marker in snapshot.",
    )
    operator_icm_tools_enabled: bool = Field(
        default=True,
        description="ICM tools in Cockpit — Link Drop, Dialogue Extract, keyword hints (on-demand, no cron).",
    )
    operator_telegram_inbound_enabled: bool = Field(
        default=True,
        description="Telegram inbound webhook for Zero-UI Hive Mode (Control Plane commands).",
    )
    operator_telegram_webhook_secret: str = Field(
        default="",
        description="Shared secret in webhook path + X-Telegram-Bot-Api-Secret-Token.",
    )
    operator_zero_ui_notify_enabled: bool = Field(
        default=True,
        description="Priority Telegram pings for verify-first outcomes (Zero-UI mode).",
    )
    proof_of_hive_enabled: bool = Field(
        default=True,
        description="HMAC-signed shareable verify receipts for artifacts (Proof-of-Hive).",
    )
    proof_of_hive_signing_secret: str = Field(
        default="",
        description="Optional dedicated HMAC secret for proof tokens; falls back to SECRET_KEY.",
    )
    hive_oracle_enabled: bool = Field(
        default=True,
        description="Hive Oracle v2 — heuristic warnings + optional LLM-light synthesis.",
    )
    hive_oracle_llm_synthesis_enabled: bool = Field(
        default=False,
        description="Enable cheap LLM synthesis in Hive Oracle (off by default for stability).",
    )
    hive_oracle_synthesis_model: str = Field(
        default="gpt-4o-mini",
        description="LiteLLM model slug for Hive Oracle synthesis when LLM enabled.",
    )
    intent_crystallizer_enabled: bool = Field(
        default=True,
        description="Intent Crystallizer v2 — free text → goal plan + deep links.",
    )
    hive_innovation_lab_enabled: bool = Field(
        default=True,
        description="Hive Innovation Lab — brainstorm → approve → Maintainer auto-implement.",
    )
    publish_hook_variants_enabled: bool = Field(
        default=True,
        description="Auto-generate hook variants on verified publish packs.",
    )
    publish_audit_enabled: bool = Field(
        default=True,
        description="Phase F — audit trail for publish queue + social publish in Execution Studio activity.",
    )
    publish_performance_enabled: bool = Field(
        default=True,
        description="Publish Performance Loop — aggregate audit into channel stats + insights.",
    )
    agent_os_enabled: bool = Field(
        default=True,
        description="Agent OS P8 — cross-swarm, imitation v2, behavioral proposals snapshot.",
    )
    analysis_swarm_enabled: bool = Field(
        default=True,
        description="Analysis Swarm — 3-lane consensus before high-risk decisions.",
    )
    analysis_swarm_min_confidence: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Minimum average confidence for Analysis Swarm execute recommendation.",
    )
    trade_to_content_enabled: bool = Field(
        default=False,
        description="Deprecated — paper trade→content pipeline removed.",
    )
    cross_swarm_knowledge_enabled: bool = Field(
        default=True,
        description="Cross-swarm recipe transfer suggestions.",
    )
    imitation_v2_enabled: bool = Field(
        default=True,
        description="Imitation v2 — auto-suggest neighbor recipes after verified outcomes.",
    )
    dreaming_behavioral_proposals_enabled: bool = Field(
        default=True,
        description="Overnight dump → behavioral instruction proposals.",
    )
    trading_overnight_review_enabled: bool = Field(
        default=True,
        description="06:00 UTC trading P&L digest for Operator Loop.",
    )
    publish_hook_optimizer_enabled: bool = Field(
        default=True,
        description="P8 #76 — recommend winning hook style per channel from publish packs.",
    )
    forager_intelligence_v2_enabled: bool = Field(
        default=True,
        description="P8 #77 — tenant forager v2 snapshot with connector gaps.",
    )
    tool_gap_signal_enabled: bool = Field(
        default=True,
        description="Record actionable MCP invoke failures per tenant (Redis, 7d TTL).",
    )
    mcp_ops_studio_live_snapshot_enabled: bool = Field(
        default=True,
        description="MCP Ops Studio reads live marketplace catalog + health metrics (fallback mock when false).",
    )
    trading_content_hybrid_enabled: bool = Field(
        default=True,
        description="P9 #80 — unified trading + publish content hybrid snapshot.",
    )
    public_trading_transparency_enabled: bool = Field(
        default=True,
        description="P9 #82 — public read-only paper trading aggregate (no secrets).",
    )
    recipe_marketplace_beta_enabled: bool = Field(
        default=True,
        description="P9 #83 — recipe marketplace beta snapshot for /recipes hub.",
    )
    research_bee_enabled: bool = Field(
        default=True,
        description="P2 #78 — NotebookLM-style URL/text → structured HiveMind brief.",
    )
    research_bee_max_chars: int = Field(
        default=12_000,
        ge=512,
        le=120_000,
        description="Max extracted characters per research bee brief.",
    )
    youtube_transcript_bee_enabled: bool = Field(
        default=True,
        description="Route YouTube URLs through transcript bee (no Data API quota).",
    )
    skill_hot_tier_enabled: bool = Field(
        default=True,
        description="Karpathy-style skill hot tier — inject only goal-matched verified recipes into Queen prompt.",
    )
    skill_hot_tier_max_recipes: int = Field(
        default=3,
        ge=1,
        le=8,
        description="Max verified recipes in skill hot tier block per session.",
    )
    skill_hot_tier_pool_size: int = Field(
        default=24,
        ge=8,
        le=64,
        description="Verified recipe pool scanned for skill hot tier matching.",
    )
    skill_hot_tier_min_score: float = Field(
        default=0.12,
        ge=0.05,
        le=1.0,
        description="Minimum token overlap score to include a recipe in hot tier.",
    )
    media_agency_in_a_box_enabled: bool = Field(
        default=True,
        description="P2 #84 — faceless media agency white-label publish lane snapshot.",
    )
    micro_saas_factory_enabled: bool = Field(
        default=True,
        description="P3 #85 — Micro-SaaS factory landing + auth + deploy blueprint.",
    )
    skill_factory_enabled: bool = Field(
        default=True,
        description="Skill Factory — research lane, tenant skills registry, GitHub export.",
    )
    skill_factory_personal_agent_publish_enabled: bool = Field(
        default=True,
        description=(
            "Auto-publish quality-passed factory skills into tenant library for agent sessions "
            "(personal in-app use — not Gumroad)."
        ),
    )
    skill_factory_research_cron_hour: int = Field(default=8, ge=0, le=23)
    skill_factory_research_cron_minute: int = Field(default=0, ge=0, le=59)
    skill_factory_external_intel_enabled: bool = Field(
        default=True,
        description="Skill Factory research uses Tavily/Serper live web signals when keys are configured.",
    )
    skill_factory_apify_probe_enabled: bool = Field(
        default=True,
        description="Light Apify actors_list probe during Skill Factory research when apify_store connector is active.",
    )
    skill_factory_apify_deep_scrape_max_per_run: int = Field(
        default=1,
        ge=0,
        le=3,
        description="Max Apify actor_run_sync calls per research run when tenant enables deep scrape.",
    )
    skill_factory_monid_intel_enabled: bool = Field(
        default=True,
        description="Allow Monid discover calls during Skill Factory research when tenant opts in.",
    )
    skill_factory_monid_max_per_run: int = Field(
        default=1,
        ge=0,
        le=3,
        description="Max Monid discover calls per research run when tenant enables listing signals.",
    )
    skill_factory_monid_video_preview_enabled: bool = Field(
        default=False,
        description="Allow Monid run on Skill Factory approve to resolve Gumroad preview video URL.",
    )
    skill_factory_github_pr_enabled: bool = Field(
        default=False,
        description="Allow Skill Factory Library → GitHub PR export via github_rest connector.",
    )
    skill_factory_github_owner: str = Field(
        default="",
        description="GitHub org/user for Skill Factory skill-pack PRs (optional).",
    )
    skill_factory_github_repo: str = Field(
        default="",
        description="GitHub repository for Skill Factory skill-pack PRs (optional).",
    )
    skill_factory_github_connector_slug: str = Field(
        default="github_rest",
        description="Dynamic connector slug for Skill Factory GitHub PR workflow.",
    )
    skill_factory_github_base_branch: str = Field(
        default="main",
        description="Base branch for Skill Factory export PRs.",
    )
    skill_factory_gumroad_listing_enabled: bool = Field(
        default=False,
        description="Allow Skill Factory Library → Gumroad draft product API.",
    )
    skill_factory_gumroad_access_token: str = Field(
        default="",
        description="Gumroad OAuth access token fallback when gumroad_rest connector is not installed.",
    )
    skill_factory_gumroad_attach_bundle_enabled: bool = Field(
        default=True,
        description="Upload GitHub pack ZIP as Gumroad deliverable after draft create.",
    )
    skill_factory_gumroad_cover_from_preview_enabled: bool = Field(
        default=True,
        description="Attach listing video_preview_url as Gumroad cover when present.",
    )
    skill_factory_gumroad_publish_enabled: bool = Field(
        default=False,
        description="Allow Library → Gumroad publish (PUT /products/:id/enable).",
    )
    content_pack_factory_enabled: bool = Field(
        default=True,
        description="Content Pack Factory — research, build, library, Gumroad-ready export.",
    )
    live_lane_snapshot_enabled: bool = Field(
        default=True,
        description="#65 — unified Polymarket + publish OAuth live lane prep snapshot.",
    )
    operator_hub_settings_enabled: bool = Field(
        default=True,
        description="Settings UI — operator hub snapshot (modules, env flags, live lane).",
    )
    execution_studio_weekly_rollup_enabled: bool = Field(
        default=True,
        description="Send weekly Execution Studio telemetry rollup via Slack/Discord/Teams webhooks and email.",
    )
    execution_studio_vapid_public_key: str = Field(
        default="",
        description="VAPID public key for Execution Studio Web Push (base64url).",
    )
    execution_studio_vapid_private_key: str = Field(
        default="",
        description="VAPID private key for Execution Studio Web Push.",
    )
    execution_studio_vapid_contact_email: str = Field(
        default="ops@queenswarm.love",
        description="mailto: contact embedded in VAPID claims for Web Push.",
    )
    supervisor_self_healing_enabled: bool = Field(
        default=True,
        description="Enable self-healing retries and reflection loop in supervisor sub-agent runtime.",
    )
    supervisor_pattern_router_enabled: bool = Field(
        default=True,
        description="Enable heuristic agentic design pattern selection at supervisor session start.",
    )
    supervisor_pattern_router_llm_enabled: bool = Field(
        default=False,
        description="Optional LLM refinement hop after heuristic pattern selection (P2).",
    )
    supervisor_forced_reflection_enabled: bool = Field(
        default=True,
        description="Force reflection pattern + self-review-loop skills on all supervisor outputs.",
    )
    queen_maintainer_enabled: bool = Field(
        default=False,
        description="Enable Queen Maintainer weekly routine and HTTP controls.",
    )
    queen_maintainer_github_owner: str = Field(
        default="",
        description="GitHub org/user for Maintainer PR workflow (optional).",
    )
    queen_maintainer_github_repo: str = Field(
        default="",
        description="GitHub repository name for Maintainer PR workflow (optional).",
    )
    queen_maintainer_github_connector_slug: str = Field(
        default="github_rest",
        description="Dynamic connector slug used for Maintainer PR creation.",
    )
    queen_maintainer_post_merge_webhook_enabled: bool = Field(
        default=False,
        description="Trigger Queen Maintainer after GitHub merge to main/master.",
    )
    queen_maintainer_github_webhook_secret: str = Field(
        default="",
        description="GitHub webhook HMAC secret (env: QUEEN_MAINTAINER_GITHUB_WEBHOOK_SECRET).",
    )
    queen_maintainer_post_merge_tenant_id: str | None = Field(
        default=None,
        description="Tenant UUID receiving post-merge Maintainer supervisor sessions.",
    )
    queen_maintainer_session_cap_usd: float = Field(
        default=0.50,
        ge=0.05,
        le=10.0,
        description="Per Maintainer supervisor session LLM spend cap (Cost Guardian).",
    )
    queen_maintainer_session_warn_ratio: float = Field(
        default=0.60,
        ge=0.1,
        le=0.95,
        description="Fraction of session cap that triggers warn state.",
    )
    queen_maintainer_daily_run_limit: int = Field(
        default=1,
        ge=1,
        le=24,
        description="Max Queen Maintainer supervisor sessions per tenant per UTC day.",
    )
    queen_maintainer_routing_mode: str = Field(
        default="economy",
        description="LiteLLM routing mode override for Maintainer lane (economy | free_first).",
    )
    queen_maintainer_researcher_model: str = Field(
        default="xai/grok-3-mini",
        description="Cheap model slug for Maintainer researcher role.",
    )
    queen_maintainer_coder_model: str = Field(
        default="xai/grok-3-mini",
        description="Cheap model slug for Maintainer coder role.",
    )
    queen_maintainer_critic_model: str = Field(
        default="openai/gpt-4o-mini",
        description="Cheap model slug for Maintainer critic role.",
    )
    queen_maintainer_self_heal_max_attempts: int = Field(
        default=1,
        ge=1,
        le=3,
        description="Self-heal retry cap for Maintainer sub-agents (cost control).",
    )
    supervisor_self_heal_max_attempts: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum self-healing attempts per sub-agent step.",
    )
    supervisor_autonomy_enabled: bool = Field(
        default=True,
        description="Allow autonomous sub-goal delegation and alternative planning without constant operator input.",
    )
    supervisor_audit_digest_enabled: bool = Field(
        default=False,
        description="Send daily supervisor session operator audit digest emails to tenant owners/admins.",
    )
    supervisor_audit_digest_window_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Rolling window for supervisor audit digest aggregation.",
    )
    supervisor_audit_digest_slack_enabled: bool = Field(
        default=True,
        description="Mirror supervisor audit digest summaries to Slack when SLACK_WEBHOOK_URL is configured.",
    )
    supervisor_audit_digest_discord_enabled: bool = Field(
        default=True,
        description="Mirror supervisor audit digest summaries to Discord when DISCORD_WEBHOOK_URL is configured.",
    )
    discord_webhook_url: str | None = Field(
        default=None,
        description="Optional global Discord incoming webhook for operator digests and alerts.",
    )
    supervisor_audit_digest_teams_enabled: bool = Field(
        default=True,
        description="Mirror supervisor audit digest summaries to Teams when TEAMS_WEBHOOK_URL is configured.",
    )
    teams_webhook_url: str | None = Field(
        default=None,
        description="Optional global Microsoft Teams incoming webhook for operator digests and alerts.",
    )
    supervisor_audit_rollup_email_enabled: bool = Field(
        default=False,
        description="Send weekly cross-tenant supervisor audit rollup to NOTIFY_EMAIL.",
    )
    supervisor_audit_rollup_window_hours: int = Field(
        default=168,
        ge=24,
        le=168,
        description="Rolling window for platform operator audit rollup email.",
    )
    supervisor_audit_rollup_cache_ttl_sec: int = Field(
        default=300,
        ge=0,
        le=3600,
        description="Redis TTL for cross-tenant audit rollup API cache (0 disables cache).",
    )
    tenant_audit_retention_enabled: bool = Field(
        default=True,
        description="Enable scheduled purge of tenant audit rows older than retention window.",
    )
    tenant_audit_retention_days: int = Field(
        default=60,
        ge=7,
        le=365,
        description="Tenant audit log retention in days before scheduled purge.",
    )
    retrieval_contract_enabled: bool = Field(
        default=False,
        description="Enable explicit retrieval contract bundles for shared context reads.",
    )
    retrieval_v2_min_relevance_score: float = Field(
        default=0.22,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score for retrieval context inclusion after hybrid ranking.",
    )
    retrieval_v2_max_items_per_section: int = Field(
        default=6,
        ge=1,
        le=32,
        description="Maximum rows retained per retrieval section after pruning.",
    )
    light_control_plane_enabled: bool = Field(
        default=False,
        description="Enable lightweight approval/reject controls on supervisor sessions.",
    )
    routines_enabled: bool = Field(
        default=False,
        description="Enable recurring/scheduled supervisor routines and Celery tick execution.",
    )
    supervisor_routine_webhook_enabled: bool = Field(
        default=True,
        description="Enable token-authenticated POST webhook ingress for event-driven supervisor routines.",
    )
    routine_watch_interval_sec: int = Field(
        default=120,
        ge=30,
        le=3600,
        description="Polling cadence for event/watch-mode routines.",
    )
    routine_history_max_entries: int = Field(
        default=50,
        ge=10,
        le=400,
        description="Maximum number of routine run history entries retained before consolidation.",
    )
    memory_evolution_enabled: bool = Field(
        default=True,
        description="Enable periodic long-term memory evolution and swarm learning synthesis.",
    )
    memory_evolution_interval_sec: int = Field(
        default=900,
        ge=120,
        le=86400,
        description="Minimum cadence for automatic long-term memory evolution ticks.",
    )
    memory_evolution_manual_approval_threshold: float = Field(
        default=0.82,
        ge=0.0,
        le=1.0,
        description="Importance score threshold above which memory changes require manual approval.",
    )
    agent_initiative_enabled: bool = Field(
        default=True,
        description="Enable self-proposed improvement suggestions from supervisor sub-agents.",
    )
    agent_initiative_auto_approve_enabled: bool = Field(
        default=True,
        description="Allow auto-approval for low-risk and low-impact initiative proposals.",
    )
    agent_initiative_auto_approve_max_risk_score: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Maximum risk score allowed for automatic initiative approval.",
    )
    agent_initiative_auto_approve_max_impact_score: float = Field(
        default=0.55,
        ge=0.0,
        le=1.0,
        description="Maximum impact score allowed for automatic initiative approval.",
    )
    swarm_full_autonomy_enabled: bool = Field(
        default=True,
        description="Enable full swarm autonomy layer that orchestrates all self-improvement subsystems.",
    )
    autonomous_routines_enabled: bool = Field(
        default=True,
        description="Enable long-horizon autonomous routine planning and execution.",
    )
    autonomous_routine_planning_horizon_hours: int = Field(
        default=72,
        ge=12,
        le=720,
        description="Planning horizon for autonomous routine checkpoints.",
    )
    browser_harness_enabled: bool = Field(
        default=True,
        description="Enable browser harness manager for browser_operator automation actions.",
    )
    browser_action_timeout_sec: int = Field(
        default=20,
        ge=3,
        le=120,
        description="Maximum timeout for one browser action.",
    )
    browser_session_ttl_sec: int = Field(
        default=240,
        ge=30,
        le=3600,
        description="Maximum lifetime of one browser harness session.",
    )
    browser_max_actions_per_session: int = Field(
        default=24,
        ge=1,
        le=200,
        description="Maximum number of actions allowed per browser session.",
    )
    browser_max_concurrent_sessions: int = Field(
        default=6,
        ge=1,
        le=32,
        description="Maximum number of active browser sessions before throttling.",
    )
    browser_instance_cpu_limit: float = Field(
        default=0.5,
        ge=0.1,
        le=4.0,
        description="Target CPU limit per browser instance (guardrail metadata).",
    )
    browser_instance_memory_mb: int = Field(
        default=256,
        ge=64,
        le=4096,
        description="Target memory limit per browser instance (guardrail metadata).",
    )
    browser_allowed_domains: list[str] = Field(
        default_factory=lambda: [
            "example.com",
            "www.example.com",
            "queenswarm.love",
        ],
        description="Allowed domain allowlist for browser harness navigation.",
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

    @model_validator(mode="after")
    def production_security_requirements(self) -> Self:
        """Apply stricter policies when production hardening mode is enabled."""

        if not self.production_security_mode:
            return self

        if len(self.secret_key.strip()) < 64:
            msg = "When PRODUCTION_SECURITY_MODE=true, SECRET_KEY must be at least 64 characters."
            raise ValueError(msg)
        if self.access_token_expire_minutes > 20:
            msg = "When PRODUCTION_SECURITY_MODE=true, ACCESS_TOKEN_EXPIRE_MINUTES must be <= 20."
            raise ValueError(msg)
        if self.refresh_token_expire_days > 90:
            msg = "When PRODUCTION_SECURITY_MODE=true, REFRESH_TOKEN_EXPIRE_DAYS must be <= 90."
            raise ValueError(msg)
        ckv = (self.connector_vault_fernet_key or "").strip()
        if not ckv:
            msg = "When PRODUCTION_SECURITY_MODE=true, CONNECTOR_VAULT_FERNET_KEY must be configured."
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def scaling_requirements(self) -> Self:
        """Enforce distributed-safe defaults when scaling mode is enabled."""

        if not self.scaling_mode_enabled:
            return self
        if self.ballroom_capsule_backend != "redis":
            msg = "When SCALING_MODE_ENABLED=true, BALLROOM_CAPSULE_BACKEND must be 'redis'."
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def single_admin_mode_requirements(self) -> Self:
        """Apply strict consistency checks for one-operator deployments."""

        if not self.single_admin_mode:
            return self
        if not self.solo_mode_enabled:
            msg = "When SINGLE_ADMIN_MODE=true, SOLO_MODE_ENABLED must also be true."
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def propagate_llm_env_aliases_for_litellm(self) -> Self:
        """Expose provider secrets under env names LiteLLM providers often expect."""

        import os

        grok = (self.grok_api_key or "").strip()
        if grok:
            os.environ.setdefault("XAI_API_KEY", grok)
            os.environ.setdefault("GROK_API_KEY", grok)
        anth = (self.anthropic_api_key or "").strip()
        if anth:
            os.environ.setdefault("ANTHROPIC_API_KEY", anth)
        oai_raw = self.openai_api_key
        oai = (str(oai_raw).strip()) if oai_raw is not None else ""
        if oai:
            os.environ.setdefault("OPENAI_API_KEY", oai)
        or_key = (self.openrouter_api_key or "").strip()
        if or_key:
            os.environ.setdefault("OPENROUTER_API_KEY", or_key)
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
