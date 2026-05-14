"""JWT-guarded swarm infrastructure diagnostics for operator consoles."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, text

from app.presentation.api.deps import JwtSubject
from app.core.logging import get_logger
from app.core.readiness import collect_readiness_uncached
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.enums import AgentStatus, TaskStatus
from app.infrastructure.persistence.models.task import Task
from app.application.services.llm_runtime_credentials import (
    provider_effective_anthropic,
    provider_effective_grok,
    provider_effective_openai,
)
from app.worker.celery_app import celery_app

logger = get_logger(__name__)

router = APIRouter(prefix="/system", tags=["System"])


class SystemStatusPayload(BaseModel):
    """High-signal dependency flags + coarse hive gauges for dashboards."""

    model_config = ConfigDict(extra="ignore")

    redis_ok: bool = Field(description="Primary Redis cache / rate-limit socket healthy.")
    celery_ok: bool = Field(description="At least one Celery consumer answered a control ping.")
    db_ok: bool = Field(description="Postgres accepted a trivial ``SELECT 1`` probe.")
    llm_ok: bool = Field(description="At least one LiteLLM provider credential is non-empty.")
    llm_grok: bool = Field(default=False, description="Grok credential present.")
    llm_anthropic: bool = Field(default=False, description="Anthropic credential present.")
    agents_total: int = Field(default=0, ge=0)
    agents_running: int = Field(default=0, ge=0)
    tasks_running: int = Field(default=0, ge=0)
    tasks_pending: int = Field(default=0, ge=0)


class NotifyTestResponse(BaseModel):
    """Results from the operator notification smoke ping."""

    message: str = Field(description="Human readable summary for dashboards.")
    results: dict[str, bool] = Field(description="Per-channel booleans keyed by slack/email.")


def _llm_flags() -> tuple[bool, bool, bool]:
    """Return aggregate flag plus per-provider booleans."""

    grok_ok = bool(provider_effective_grok())
    anth_ok = bool(provider_effective_anthropic())
    open_ok = bool(provider_effective_openai())
    llm_ok = bool(grok_ok or anth_ok or open_ok)
    return llm_ok, grok_ok, anth_ok


async def _postgres_singleton_select() -> None:
    """Run a tiny query using a fresh session (duplicates readiness semantics)."""

    from app.core.database import async_session

    async with async_session() as session:
        await session.execute(text("SELECT 1"))


async def _hive_gauges() -> tuple[int, int, int, int]:
    """Count agents/tasks for Neon KPI tiles."""

    from app.core.database import async_session

    async with async_session() as session:
        agents_total = int((await session.execute(select(func.count()).select_from(Agent))).scalar() or 0)
        agents_running = int(
            (
                await session.execute(
                    select(func.count()).select_from(Agent).where(Agent.status == AgentStatus.RUNNING),
                )
            ).scalar()
            or 0,
        )
        tasks_running = int(
            (
                await session.execute(
                    select(func.count()).select_from(Task).where(Task.status == TaskStatus.RUNNING),
                )
            ).scalar()
            or 0,
        )
        tasks_pending = int(
            (
                await session.execute(
                    select(func.count()).select_from(Task).where(Task.status == TaskStatus.PENDING),
                )
            ).scalar()
            or 0,
        )
        return agents_total, agents_running, tasks_running, tasks_pending


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
    llm_ok, grok_ok, anth_ok = _llm_flags()

    agents_total = agents_running = tasks_running = tasks_pending = 0
    if db_second_opinion:
        try:
            agents_total, agents_running, tasks_running, tasks_pending = await _hive_gauges()
        except Exception as exc:  # noqa: BLE001
            logger.warning("system.status.hive_gauges_failed", error=str(exc))

    return SystemStatusPayload(
        redis_ok=redis_ok,
        celery_ok=celery_ok,
        db_ok=db_second_opinion,
        llm_ok=llm_ok,
        llm_grok=grok_ok,
        llm_anthropic=anth_ok,
        agents_total=agents_total,
        agents_running=agents_running,
        tasks_running=tasks_running,
        tasks_pending=tasks_pending,
    )


@router.post("/notify-test", summary="Smoke-test Slack + SMTP wiring", response_model=NotifyTestResponse)
async def post_notify_test(_subject: JwtSubject) -> NotifyTestResponse:
    """Trigger optional Slack/email notifications using ``settings``."""

    from app.core.notifications import notify_email, notify_slack

    results: dict[str, bool] = {
        "slack": await notify_slack(
            "🐝 Test notification from Queenswarm! Everything is working.",
            color="#00FF88",
            title="Test",
        ),
        "email": await notify_email(
            subject="Test Notification",
            body="🐝 Test notification from Queenswarm! Everything is working.",
        ),
    }
    sent = [channel for channel, ok in results.items() if ok]
    skipped = [channel for channel, ok in results.items() if not ok]

    hint = ""
    if not sent:
        hint = (
            "(configure SLACK_WEBHOOK_URL plus SMTP_* + NOTIFY_EMAIL in `.env`; then restart backend.)"
            if skipped
            else ""
        )

    summary = (
        f"Channels delivered: {', '.join(sent) or 'none'}. "
        f"Skipped: {', '.join(skipped) or 'none'}. "
        f"{hint}"
    ).strip()

    logger.info(
        "system.notify_test",
        slack=results["slack"],
        email=results["email"],
    )

    return NotifyTestResponse(message=summary, results=results)


__all__ = ["NotifyTestResponse", "router", "SystemStatusPayload"]
