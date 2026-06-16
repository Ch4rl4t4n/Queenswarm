"""Track O TJ4 — Learning Loop Studio settings (fields, review cron, Obsidian, mistake tags)."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.routine_service import create_supervisor_routine
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

JOURNAL_STUDIO_SETTINGS_KEY = "journal_studio"
ROUTINE_NAME = "Trading journal review"
JOURNAL_REVIEW_LANE = "journal_studio_review"

ReviewCronPreset = Literal["off", "daily_0600", "daily_2000", "weekly_monday", "custom"]
RoutineStatus = Literal["missing", "scheduled", "running", "ready", "disabled"]

CRON_FIELD_RE = re.compile(r"^[\d*,/-]+$")

DEFAULT_FIELD_TOGGLES: dict[str, bool] = {
    "thesis": True,
    "setup": True,
    "entry_price": True,
    "exit_price": True,
    "position_size": True,
    "outcome": True,
    "pnl": True,
    "emotion": True,
    "screenshot": False,
    "lesson": True,
    "tags": True,
    "mistake_tag": True,
}

DEFAULT_MISTAKE_TAGS: list[str] = [
    "fomo",
    "revenge_trade",
    "no_stop",
    "oversized",
    "early_exit",
    "late_entry",
    "ignored_plan",
    "chased_price",
]

REVIEW_CRON_PRESETS: dict[str, str] = {
    "daily_0600": "0 6 * * *",
    "daily_2000": "0 20 * * *",
    "weekly_monday": "0 7 * * 1",
}

GOAL_TEMPLATE = """\
Trading journal review (verify-first, operator approve before vault write).

Review recent paper fills and manual journal entries for this tenant:
1. Summarize what worked and repeat mistakes (use configured mistake tags).
2. Draft Obsidian-ready markdown for operator approval — never write vault without HITL.
3. Cross-link thesis brief (NP5) when available.
4. Tag entries for pattern strip (30d / 90d) — simulate export only.

Skills: trading-journal-playbook, self-review-loop, obsidian-export-playbook.
Save deliverable tagged journal-review. Operator approve before Obsidian sync.
""".strip()


class JournalStudioSettingsOut(BaseModel):
    """Tenant journal studio configuration snapshot."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    field_toggles: dict[str, bool] = Field(default_factory=lambda: dict(DEFAULT_FIELD_TOGGLES))
    review_cron_enabled: bool = True
    review_cron_preset: ReviewCronPreset = "daily_0600"
    review_cron: str = "0 6 * * *"
    obsidian_subfolder: str = "Trading/Journal"
    mistake_tags: list[str] = Field(default_factory=lambda: list(DEFAULT_MISTAKE_TAGS))
    source: Literal["deployment", "tenant"] = "deployment"
    updated_at: datetime | None = None
    workspace_href: str = "/apps-tools/trading-journal?section=settings#journal-studio-settings"


class JournalStudioSettingsPatchIn(BaseModel):
    """Operator PATCH body for journal studio settings."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    field_toggles: dict[str, bool] | None = None
    review_cron_enabled: bool | None = None
    review_cron_preset: ReviewCronPreset | None = None
    review_cron: str | None = None
    obsidian_subfolder: str | None = None
    mistake_tags: list[str] | None = None

    @field_validator("obsidian_subfolder")
    @classmethod
    def _sanitize_subfolder(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().strip("/").replace("\\", "/")
        if not cleaned:
            msg = "Obsidian subfolder cannot be empty."
            raise ValueError(msg)
        if ".." in cleaned.split("/"):
            msg = "Obsidian subfolder cannot contain parent path segments."
            raise ValueError(msg)
        return cleaned[:240]

    @field_validator("mistake_tags")
    @classmethod
    def _sanitize_mistake_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        seen: set[str] = set()
        out: list[str] = []
        for raw in value:
            tag = str(raw).strip().lower().replace(" ", "_")[:48]
            if not tag or tag in seen:
                continue
            seen.add(tag)
            out.append(tag)
        if not out:
            msg = "At least one mistake tag is required."
            raise ValueError(msg)
        return out[:32]


class JournalStudioRoutineKpiOut(BaseModel):
    """Review routine KPI strip for trading journal workspace."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    routine_status: RoutineStatus = "missing"
    routine_id: str | None = None
    routine_name: str = ROUTINE_NAME
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    last_session_status: str | None = None
    last_session_href: str | None = None
    review_cron: str = "0 6 * * *"
    review_cron_preset: ReviewCronPreset = "daily_0600"
    obsidian_subfolder: str = "Trading/Journal"
    enabled_field_count: int = 0
    mistake_tag_count: int = 0
    operator_hint: str = ""
    workspace_href: str = "/apps-tools/trading-journal?section=settings#journal-studio-settings"


def _deployment_defaults() -> JournalStudioSettingsOut:
    preset_raw = settings.journal_studio_default_review_cron_preset
    preset: ReviewCronPreset = "daily_0600"
    if preset_raw in {"off", "daily_0600", "daily_2000", "weekly_monday", "custom"}:
        preset = preset_raw  # type: ignore[assignment]
    cron = resolve_review_cron(preset, settings.journal_studio_default_review_cron)
    return JournalStudioSettingsOut(
        enabled=settings.journal_studio_enabled,
        field_toggles=dict(DEFAULT_FIELD_TOGGLES),
        review_cron_enabled=settings.journal_studio_review_routine_enabled,
        review_cron_preset=preset,
        review_cron=cron,
        obsidian_subfolder=settings.journal_studio_default_obsidian_subfolder,
        mistake_tags=list(DEFAULT_MISTAKE_TAGS),
        source="deployment",
    )


def _settings_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get(JOURNAL_STUDIO_SETTINGS_KEY)
    return dict(bucket) if isinstance(bucket, dict) else {}


def validate_cron_expr(expr: str) -> str:
    """Validate 5-field cron expression (minute hour dom month dow)."""

    parts = expr.strip().split()
    if len(parts) != 5:
        msg = "Cron must have exactly 5 fields (minute hour day month weekday)."
        raise ValueError(msg)
    for part in parts:
        if not CRON_FIELD_RE.match(part):
            msg = f"Invalid cron field: {part!r}"
            raise ValueError(msg)
    return " ".join(parts)


def resolve_review_cron(preset: str, custom: str | None = None) -> str:
    """Resolve cron expression from preset or custom value."""

    if preset == "off":
        return "0 6 * * *"
    if preset == "custom":
        return validate_cron_expr(custom or settings.journal_studio_default_review_cron)
    if preset in REVIEW_CRON_PRESETS:
        return REVIEW_CRON_PRESETS[preset]
    return validate_cron_expr(settings.journal_studio_default_review_cron)


def merge_field_toggles(raw: dict[str, Any] | None) -> dict[str, bool]:
    """Merge tenant field toggles over defaults."""

    merged = dict(DEFAULT_FIELD_TOGGLES)
    if isinstance(raw, dict):
        for key in DEFAULT_FIELD_TOGGLES:
            if key in raw:
                merged[key] = bool(raw[key])
    return merged


def enabled_field_keys(field_toggles: dict[str, bool]) -> list[str]:
    """Return enabled journal field keys."""

    return [key for key, enabled in field_toggles.items() if enabled]


def _settings_from_bucket(bucket: dict[str, Any]) -> JournalStudioSettingsOut:
    base = _deployment_defaults()
    if not bucket:
        return base
    preset_raw = str(bucket.get("review_cron_preset", base.review_cron_preset))
    preset: ReviewCronPreset
    if preset_raw in {"off", "daily_0600", "daily_2000", "weekly_monday", "custom"}:
        preset = preset_raw  # type: ignore[assignment]
    else:
        preset = base.review_cron_preset
    cron_raw = bucket.get("review_cron")
    cron = resolve_review_cron(preset, str(cron_raw) if cron_raw is not None else None)
    tags_raw = bucket.get("mistake_tags")
    tags = list(DEFAULT_MISTAKE_TAGS)
    if isinstance(tags_raw, list):
        try:
            tags = JournalStudioSettingsPatchIn.model_validate({"mistake_tags": tags_raw}).mistake_tags or tags
        except ValueError:
            tags = list(DEFAULT_MISTAKE_TAGS)
    merged = base.model_copy(
        update={
            "enabled": bool(bucket.get("enabled", base.enabled)),
            "field_toggles": merge_field_toggles(bucket.get("field_toggles")),
            "review_cron_enabled": bool(bucket.get("review_cron_enabled", base.review_cron_enabled)),
            "review_cron_preset": preset,
            "review_cron": cron,
            "obsidian_subfolder": str(bucket.get("obsidian_subfolder", base.obsidian_subfolder)),
            "mistake_tags": tags,
            "source": "tenant",
            "updated_at": bucket.get("updated_at"),
        },
    )
    return JournalStudioSettingsOut.model_validate(merged.model_dump(mode="python"))


async def get_journal_studio_settings(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> JournalStudioSettingsOut:
    """Load tenant journal studio settings."""

    tenant = await session.get(Tenant, tenant_id)
    bucket = _settings_bucket(tenant.operator_settings if tenant else None)
    return _settings_from_bucket(bucket)


async def save_journal_studio_settings(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    patch: JournalStudioSettingsPatchIn,
) -> JournalStudioSettingsOut:
    """Persist tenant journal studio overrides."""

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        msg = f"Tenant {tenant_id} not found"
        raise ValueError(msg)

    current = await get_journal_studio_settings(session, tenant_id=tenant_id)
    data = current.model_dump(mode="python")
    patch_data = patch.model_dump(exclude_unset=True)
    for key, value in patch_data.items():
        if value is not None:
            data[key] = value
    preset = data.get("review_cron_preset", current.review_cron_preset)
    cron_override = patch.review_cron if patch.review_cron is not None else data.get("review_cron")
    data["review_cron"] = resolve_review_cron(str(preset), str(cron_override) if cron_override else None)
    if preset == "off":
        data["review_cron_enabled"] = False
    data["field_toggles"] = merge_field_toggles(data.get("field_toggles"))
    data["source"] = "tenant"
    data["updated_at"] = datetime.now(tz=UTC).isoformat()
    saved = JournalStudioSettingsOut.model_validate(data)

    root = dict(tenant.operator_settings or {})
    existing_bucket = dict(root.get(JOURNAL_STUDIO_SETTINGS_KEY) or {})
    manual_entries = existing_bucket.get("manual_entries")
    root[JOURNAL_STUDIO_SETTINGS_KEY] = {
        "enabled": saved.enabled,
        "field_toggles": saved.field_toggles,
        "review_cron_enabled": saved.review_cron_enabled,
        "review_cron_preset": saved.review_cron_preset,
        "review_cron": saved.review_cron,
        "obsidian_subfolder": saved.obsidian_subfolder,
        "mistake_tags": saved.mistake_tags,
        "updated_at": saved.updated_at,
    }
    if isinstance(manual_entries, list):
        root[JOURNAL_STUDIO_SETTINGS_KEY]["manual_entries"] = manual_entries
    pending_drafts = existing_bucket.get("pending_drafts")
    if isinstance(pending_drafts, list):
        root[JOURNAL_STUDIO_SETTINGS_KEY]["pending_drafts"] = pending_drafts
    for meta_key in ("gardener_last_run_at", "gardener_last_run_drafts_created"):
        if meta_key in existing_bucket:
            root[JOURNAL_STUDIO_SETTINGS_KEY][meta_key] = existing_bucket[meta_key]
    tenant.operator_settings = root
    await session.flush()
    _logger.info(
        "journal_studio.settings_saved",
        agent_id="journal_studio",
        swarm_id=str(tenant_id),
        enabled=saved.enabled,
        review_cron=saved.review_cron,
        obsidian_subfolder=saved.obsidian_subfolder,
    )
    return saved


async def ensure_journal_review_routine(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    created_by_subject: str | None = None,
) -> dict[str, object]:
    """Idempotently register trading journal review supervisor routine."""

    if not settings.journal_studio_enabled or not settings.journal_studio_review_routine_enabled:
        return {"status": "disabled", "routine_id": None}

    studio = await get_journal_studio_settings(session, tenant_id=tenant_id)
    if not studio.enabled or not studio.review_cron_enabled or studio.review_cron_preset == "off":
        return {"status": "disabled", "routine_id": None, "reason": "review_cron_off"}

    cron_expr = studio.review_cron
    existing = await session.scalar(
        select(SupervisorRoutine)
        .where(
            SupervisorRoutine.tenant_id == tenant_id,
            SupervisorRoutine.name == ROUTINE_NAME,
        )
        .limit(1),
    )
    if existing is not None:
        if existing.cron_expr != cron_expr:
            existing.cron_expr = cron_expr
            await session.flush()
        return {
            "status": "exists",
            "routine_id": str(existing.id),
            "next_run_at": existing.next_run_at.isoformat() if existing.next_run_at else None,
            "schedule": cron_expr,
        }

    row = await create_supervisor_routine(
        session,
        name=ROUTINE_NAME,
        goal_template=GOAL_TEMPLATE,
        created_by_subject=created_by_subject or "system:journal-studio-review",
        schedule_kind="cron",
        interval_seconds=None,
        cron_expr=cron_expr,
        runtime_mode="durable",
        roles=["orchestrator", "researcher", "critic"],
        retrieval_contract="customer_history+policy+last_3_tasks",
        skills=["trading-journal-playbook", "self-review-loop", "obsidian-export-playbook"],
        context_payload={
            "lane": JOURNAL_REVIEW_LANE,
            "simulate_first": True,
            "obsidian_subfolder": studio.obsidian_subfolder,
            "mistake_tags": studio.mistake_tags,
            "enabled_fields": enabled_field_keys(studio.field_toggles),
        },
        tenant_id=tenant_id,
    )
    await session.flush()
    _logger.info(
        "journal_studio.review_routine_created",
        agent_id="journal_studio",
        swarm_id=str(tenant_id),
        routine_id=str(row.id),
        schedule=cron_expr,
    )
    return {
        "status": "created",
        "routine_id": str(row.id),
        "next_run_at": row.next_run_at.isoformat() if row.next_run_at else None,
        "schedule": cron_expr,
    }


async def _latest_routine_session(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    routine_id: uuid.UUID,
) -> SupervisorSession | None:
    return await session.scalar(
        select(SupervisorSession)
        .where(
            SupervisorSession.tenant_id == tenant_id,
            SupervisorSession.context_summary["routine_id"].astext == str(routine_id),
        )
        .order_by(desc(SupervisorSession.started_at))
        .limit(1),
    )


async def compose_journal_studio_routine_kpi(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> JournalStudioRoutineKpiOut:
    """Compose review routine KPI for trading journal workspace."""

    studio = await get_journal_studio_settings(session, tenant_id=tenant_id)
    enabled_count = len(enabled_field_keys(studio.field_toggles))
    if not settings.journal_studio_enabled or not studio.enabled:
        return JournalStudioRoutineKpiOut(
            enabled=False,
            routine_status="disabled",
            review_cron=studio.review_cron,
            review_cron_preset=studio.review_cron_preset,
            obsidian_subfolder=studio.obsidian_subfolder,
            enabled_field_count=enabled_count,
            mistake_tag_count=len(studio.mistake_tags),
            operator_hint="Enable journal studio in settings to schedule reviews.",
        )

    if not studio.review_cron_enabled or studio.review_cron_preset == "off":
        return JournalStudioRoutineKpiOut(
            enabled=True,
            routine_status="disabled",
            review_cron=studio.review_cron,
            review_cron_preset=studio.review_cron_preset,
            obsidian_subfolder=studio.obsidian_subfolder,
            enabled_field_count=enabled_count,
            mistake_tag_count=len(studio.mistake_tags),
            operator_hint="Turn on review cron or bootstrap routine to schedule overnight reviews.",
        )

    routine = await session.scalar(
        select(SupervisorRoutine)
        .where(
            SupervisorRoutine.tenant_id == tenant_id,
            SupervisorRoutine.name == ROUTINE_NAME,
        )
        .limit(1),
    )
    if routine is None:
        return JournalStudioRoutineKpiOut(
            enabled=True,
            routine_status="missing",
            review_cron=studio.review_cron,
            review_cron_preset=studio.review_cron_preset,
            obsidian_subfolder=studio.obsidian_subfolder,
            enabled_field_count=enabled_count,
            mistake_tag_count=len(studio.mistake_tags),
            operator_hint="Bootstrap review routine to register cron with supervisor.",
        )

    last_session = await _latest_routine_session(session, tenant_id=tenant_id, routine_id=routine.id)
    status: RoutineStatus = "scheduled"
    if last_session is not None:
        if last_session.status in {"running", "needs_input"}:
            status = "running"
        elif last_session.status == "completed":
            status = "ready"

    last_href = None
    if last_session is not None:
        last_href = f"/agents/sessions/{last_session.id}"

    return JournalStudioRoutineKpiOut(
        enabled=True,
        routine_status=status,
        routine_id=str(routine.id),
        next_run_at=routine.next_run_at,
        last_run_at=last_session.started_at if last_session else None,
        last_session_status=last_session.status if last_session else None,
        last_session_href=last_href,
        review_cron=studio.review_cron,
        review_cron_preset=studio.review_cron_preset,
        obsidian_subfolder=studio.obsidian_subfolder,
        enabled_field_count=enabled_count,
        mistake_tag_count=len(studio.mistake_tags),
        operator_hint="Review routine active — drafts await operator approve before vault write.",
    )


__all__ = [
    "DEFAULT_FIELD_TOGGLES",
    "DEFAULT_MISTAKE_TAGS",
    "GOAL_TEMPLATE",
    "JOURNAL_REVIEW_LANE",
    "JOURNAL_STUDIO_SETTINGS_KEY",
    "JournalStudioRoutineKpiOut",
    "JournalStudioSettingsOut",
    "JournalStudioSettingsPatchIn",
    "ROUTINE_NAME",
    "compose_journal_studio_routine_kpi",
    "enabled_field_keys",
    "ensure_journal_review_routine",
    "get_journal_studio_settings",
    "merge_field_toggles",
    "resolve_review_cron",
    "save_journal_studio_settings",
    "validate_cron_expr",
]
