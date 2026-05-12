"""JWT-guarded swarm infrastructure diagnostics for operator consoles."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

from app.api.deps import JwtSubject
from app.core.config import settings
from app.core.logging import get_logger
from app.core.readiness import collect_readiness_uncached
from app.worker.celery_app import celery_app

logger = get_logger(__name__)

router = APIRouter(prefix="/system", tags=["System"])


class SystemStatusPayload(BaseModel):
    """High-signal dependency flags for /costs dashboards."""

    model_config = ConfigDict(extra="ignore")

    redis_ok: bool = Field(description="Primary Redis cache / rate-limit socket healthy.")
    celery_ok: bool = Field(description="At least one Celery consumer answered a control ping.")
    db_ok: bool = Field(description="Postgres accepted a trivial ``SELECT 1`` probe.")
    llm_ok: bool = Field(description="At least one LiteLLM provider credential is non-empty.")


def _llm_configured() -> bool:
    grok = (settings.grok_api_key or "").strip()
    claude = (settings.anthropic_api_key or "").strip()
    openai = (settings.openai_api_key or "").strip()
    return bool(grok or claude or openai)


async def _postgres_singleton_select() -> None:
    """Run a tiny query using a fresh session (duplicates readiness semantics)."""

    from app.core.database import async_session

    async with async_session() as session:
        await session.execute(text("SELECT 1"))


def _celery_workers_respond() -> bool:
    """Return ``True`` when ``inspect.ping`` sees an active consumer."""

    try:
        inspector = celery_app.control.inspect(timeout=1.5)
        if inspector is None:
            return False
        ping: dict[str, Any] | None = inspector.ping()
        return bool(ping)
    except Exception as exc:  # noqa: BLE001 — defensive operator surface
        logger.warning("system.status.celery_inspect_failed", error=str(exc))
        return False


@router.get(
    "/status",
    summary="Infrastructure snapshot (Redis/Celery/DB/LLM)",
    response_model=SystemStatusPayload,
)
async def read_system_status(_subject: JwtSubject) -> SystemStatusPayload:
    """Expose lightweight infra checks consumed by hive dashboards."""

    payload, _ = await collect_readiness_uncached()
    checks = payload.get("checks") or {}
    redis_layer = checks.get("redis") or {}
    postgres_layer = checks.get("postgres") or {}
    redis_ok = bool(redis_layer.get("ok"))
    db_via_readiness = bool(postgres_layer.get("ok"))

    db_second_opinion = db_via_readiness
    if not db_second_opinion:
        try:
            await _postgres_singleton_select()
            db_second_opinion = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("system.status.db_direct_failed", error=str(exc))

    celery_ok = await asyncio.to_thread(_celery_workers_respond)
    llm_ok = _llm_configured()

    return SystemStatusPayload(
        redis_ok=redis_ok,
        celery_ok=celery_ok,
        db_ok=db_second_opinion,
        llm_ok=llm_ok,
    )


__all__ = ["router", "SystemStatusPayload"]
