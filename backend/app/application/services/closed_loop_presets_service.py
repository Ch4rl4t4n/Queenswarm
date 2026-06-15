"""LOOP5 — Closed-loop presets for Factory, social intel, publish/SEO bulk."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.closed_review_loop_service import (
    ClosedReviewLoopRunIn,
    run_closed_review_loop,
)
from app.application.services.loop_guardrails_service import (
    LoopGuardrailsPolicyPatchIn,
    get_loop_guardrails_policy,
    save_loop_guardrails_policy,
)
from app.application.services.mission_kanban import create_mission_triage_task
from app.application.services.rubric_templates import get_rubric_template
from app.core.config import settings
from app.core.logging import get_logger
from app.domain.outputs.engine import OutputEngine

_logger = get_logger(__name__)

CLOSED_LOOP_PRESETS_SETTINGS_KEY = "closed_loop_presets"

ClosedLoopPresetId = Literal["factory_forge", "social_intel", "publish_bulk", "seo_bulk"]
ClosedLoopPresetLane = Literal["factory", "social", "marketing", "seo"]


class ClosedLoopPresetOut(BaseModel):
    """One reusable closed-loop configuration."""

    model_config = ConfigDict(extra="ignore")

    preset_id: ClosedLoopPresetId
    label: str
    description: str
    lane: ClosedLoopPresetLane
    rubric_template_id: str
    max_turns: int = Field(ge=1, le=25)
    min_score: float = Field(ge=0.0, le=1.0)
    cost_cap_usd: float = Field(ge=0.05, le=50.0)
    simulate_only: bool = False
    href: str = ""


class ClosedLoopPresetsSnapshotOut(BaseModel):
    """Catalog + tenant active preset."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    presets: list[ClosedLoopPresetOut] = Field(default_factory=list)
    active_preset_id: ClosedLoopPresetId | None = None
    active_rubric_template_id: str | None = None
    policy_source: str = "deployment"


class ClosedLoopPresetApplyIn(BaseModel):
    """Apply preset to tenant LOOP2 guardrails."""

    model_config = ConfigDict(extra="forbid")

    preset_id: ClosedLoopPresetId


class ClosedLoopPresetApplyOut(BaseModel):
    """Result after applying preset."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    preset_id: ClosedLoopPresetId
    label: str
    rubric_template_id: str
    max_turns: int
    min_score: float
    message: str = ""


class SocialIntelScoreIn(BaseModel):
    """Score scraped intel copy and optionally create Kanban task."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=8, max_length=12_000)
    title: str | None = Field(default=None, min_length=3, max_length=500)
    source_url: str | None = Field(default=None, max_length=2048)
    create_task: bool = True


class SocialIntelScoreOut(BaseModel):
    """LOOP5 social intel score → task outcome."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    passed: bool
    score: float | None = None
    min_score: float
    template_id: str
    task_id: str | None = None
    deliverable_id: str | None = None
    href: str | None = None
    message: str = ""


CLOSED_LOOP_PRESETS: tuple[ClosedLoopPresetOut, ...] = (
    ClosedLoopPresetOut(
        preset_id="factory_forge",
        label="Skill Factory critic loop",
        description="Forge queue builds — code-review rubric, 6 turns, ≥4/5 before export.",
        lane="factory",
        rubric_template_id="code-review",
        max_turns=6,
        min_score=0.8,
        cost_cap_usd=0.75,
        href="/factory?tab=queue#factory-queue-slo",
    ),
    ClosedLoopPresetOut(
        preset_id="social_intel",
        label="Social intel score → task",
        description="Evaluator after scrape — copy-marketing rubric, auto triage when pass.",
        lane="social",
        rubric_template_id="copy-marketing",
        max_turns=4,
        min_score=0.75,
        cost_cap_usd=0.4,
        href="/foragers",
    ),
    ClosedLoopPresetOut(
        preset_id="publish_bulk",
        label="Publish bulk copy (simulate-only)",
        description="Marketing carousel variants — marketing-creative rubric, simulate-first.",
        lane="marketing",
        rubric_template_id="marketing-creative",
        max_turns=4,
        min_score=0.75,
        cost_cap_usd=0.5,
        simulate_only=True,
        href="/apps-tools/marketing-automation?section=launch#campaign-launch-wizard",
    ),
    ClosedLoopPresetOut(
        preset_id="seo_bulk",
        label="SEO bulk pages (simulate-only)",
        description="Formula landing pages — copy-marketing rubric, no live publish without HITL.",
        lane="seo",
        rubric_template_id="copy-marketing",
        max_turns=5,
        min_score=0.7,
        cost_cap_usd=0.6,
        simulate_only=True,
        href="/apps-tools/marketing-automation?section=publish#social-publish",
    ),
)


def get_closed_loop_preset(preset_id: str) -> ClosedLoopPresetOut | None:
    """Return preset by id or None."""

    for preset in CLOSED_LOOP_PRESETS:
        if preset.preset_id == preset_id:
            return preset
    return None


def list_closed_loop_presets() -> list[ClosedLoopPresetOut]:
    """Return all LOOP5 presets."""

    return list(CLOSED_LOOP_PRESETS)


def _load_presets_bucket(tenant) -> dict[str, object]:  # noqa: ANN001
    root = dict(getattr(tenant, "operator_settings", None) or {})
    raw = root.get(CLOSED_LOOP_PRESETS_SETTINGS_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


async def compose_closed_loop_presets_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> ClosedLoopPresetsSnapshotOut:
    """Return preset catalog and tenant active selection."""

    if not settings.closed_loop_presets_enabled:
        return ClosedLoopPresetsSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            presets=[],
        )

    from app.infrastructure.persistence.models.tenant import Tenant

    tenant = await session.get(Tenant, tenant_id)
    bucket = _load_presets_bucket(tenant)
    active_raw = str(bucket.get("active_preset_id") or "").strip()
    active: ClosedLoopPresetId | None = None
    if active_raw in {row.preset_id for row in CLOSED_LOOP_PRESETS}:
        active = active_raw  # type: ignore[assignment]

    policy = await get_loop_guardrails_policy(session, tenant_id=tenant_id)
    rubric_id = str(bucket.get("active_rubric_template_id") or "").strip() or None
    if not rubric_id and active:
        preset = get_closed_loop_preset(active)
        rubric_id = preset.rubric_template_id if preset else None

    return ClosedLoopPresetsSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        presets=list_closed_loop_presets(),
        active_preset_id=active,
        active_rubric_template_id=rubric_id,
        policy_source=policy.source,
    )


async def apply_closed_loop_preset(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    body: ClosedLoopPresetApplyIn,
) -> ClosedLoopPresetApplyOut:
    """Apply LOOP5 preset to tenant loop guardrails + store active rubric."""

    if not settings.closed_loop_presets_enabled:
        raise ValueError("Closed-loop presets are disabled.")

    preset = get_closed_loop_preset(body.preset_id)
    if preset is None:
        raise ValueError(f"Unknown closed-loop preset: {body.preset_id}")

    if get_rubric_template(preset.rubric_template_id) is None:
        raise ValueError(f"Rubric template missing: {preset.rubric_template_id}")

    await save_loop_guardrails_policy(
        session,
        tenant_id=tenant_id,
        patch=LoopGuardrailsPolicyPatchIn(
            enabled=True,
            max_turns=preset.max_turns,
            min_score=preset.min_score,
            cost_cap_usd=preset.cost_cap_usd,
        ),
    )

    from app.infrastructure.persistence.models.tenant import Tenant

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError(f"Tenant {tenant_id} not found")

    root = dict(tenant.operator_settings or {})
    root[CLOSED_LOOP_PRESETS_SETTINGS_KEY] = {
        "active_preset_id": preset.preset_id,
        "active_rubric_template_id": preset.rubric_template_id,
        "applied_at": datetime.now(tz=UTC).isoformat(),
        "simulate_only": preset.simulate_only,
    }
    tenant.operator_settings = root
    await session.flush()

    _logger.info(
        "closed_loop_presets.applied",
        agent_id="closed_loop_presets",
        swarm_id=str(tenant_id),
        preset_id=preset.preset_id,
        rubric=preset.rubric_template_id,
    )

    sim_note = " Simulate-only — no live publish without operator OK." if preset.simulate_only else ""
    return ClosedLoopPresetApplyOut(
        ok=True,
        preset_id=preset.preset_id,
        label=preset.label,
        rubric_template_id=preset.rubric_template_id,
        max_turns=preset.max_turns,
        min_score=preset.min_score,
        message=f"Applied {preset.label} — LOOP2 guardrails updated.{sim_note}",
    )


async def get_active_loop5_preset_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> ClosedLoopPresetOut | None:
    """Load tenant active LOOP5 preset if set."""

    from app.infrastructure.persistence.models.tenant import Tenant

    tenant = await session.get(Tenant, tenant_id)
    bucket = _load_presets_bucket(tenant)
    preset_id = str(bucket.get("active_preset_id") or "").strip()
    return get_closed_loop_preset(preset_id) if preset_id else None


async def run_social_intel_score_to_task(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    body: SocialIntelScoreIn,
) -> SocialIntelScoreOut:
    """LOOP5 social intel — score copy with preset rubric; triage task on pass."""

    if not settings.closed_loop_presets_enabled:
        raise ValueError("Closed-loop presets are disabled.")

    preset = get_closed_loop_preset("social_intel")
    if preset is None:
        raise ValueError("Social intel preset unavailable.")

    loop_result = await run_closed_review_loop(
        session,
        tenant_id=tenant_id,
        body=ClosedReviewLoopRunIn(
            text=body.text.strip(),
            template_id=preset.rubric_template_id,
            max_turns=preset.max_turns,
            min_score=preset.min_score,
            task_id="social_intel_loop5",
        ),
    )

    last_score = loop_result.iterations[-1].score if loop_result.iterations else None
    task_id: str | None = None
    deliverable_id: str | None = None
    href: str | None = None

    if loop_result.passed and body.create_task:
        title = (body.title or "").strip() or "Social intel brief (LOOP5 pass)"
        markdown = (
            f"# {title}\n\n"
            f"_Social intel closed loop PASS — score {last_score:.0%} vs {preset.min_score:.0%}._\n\n"
            f"Source: {body.source_url or 'pasted intel'}\n\n"
            f"---\n\n{loop_result.final_text.strip()}\n"
        )
        triage = await create_mission_triage_task(
            session,
            task_text=markdown,
            title=title,
            priority=5,
            swarm_id=None,
            skills=["social-intel-evaluator", "context"],
            extra_payload={
                "loop5_social_intel": True,
                "source_url": body.source_url,
                "rubric_score": last_score,
            },
        )
        task_id = str(triage.task.id)
        deliverable = await OutputEngine.create_final_deliverable(
            session,
            lineage_id=uuid.uuid4(),
            markdown_body=markdown,
            structured={
                "format": "queenswarm.social_intel_loop5.v1",
                "source_url": body.source_url,
                "score": last_score,
                "template_id": preset.rubric_template_id,
            },
            title_hint=title,
            slug_hint="social-intel-loop5",
            tags=["social-intel", "loop5", "verified-intel"],
            voice_script=None,
            dashboard_user_id=dashboard_user_id,
            ballroom_session_id=None,
            mission_id=triage.task.id,
            source_task_id=triage.task.id,
        )
        deliverable_id = str(deliverable.id)
        href = f"/tasks?task={task_id}"

    message = loop_result.message
    if loop_result.passed and task_id:
        message = f"{message} Kanban triage created."

    return SocialIntelScoreOut(
        ok=True,
        passed=loop_result.passed,
        score=last_score,
        min_score=preset.min_score,
        template_id=preset.rubric_template_id,
        task_id=task_id,
        deliverable_id=deliverable_id,
        href=href,
        message=message,
    )


__all__ = [
    "CLOSED_LOOP_PRESETS",
    "CLOSED_LOOP_PRESETS_SETTINGS_KEY",
    "ClosedLoopPresetApplyIn",
    "ClosedLoopPresetApplyOut",
    "ClosedLoopPresetOut",
    "ClosedLoopPresetsSnapshotOut",
    "SocialIntelScoreIn",
    "SocialIntelScoreOut",
    "apply_closed_loop_preset",
    "compose_closed_loop_presets_snapshot",
    "get_active_loop5_preset_for_tenant",
    "get_closed_loop_preset",
    "list_closed_loop_presets",
    "run_social_intel_score_to_task",
]
