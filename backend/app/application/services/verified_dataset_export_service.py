"""Track M LOC5 — Verified dataset export (critic-approved → Alpaca JSONL)."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.loop_guardrails_service import last_rubric_score_from_summary
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.recipe import Recipe
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable

_logger = get_logger(__name__)

VerifiedDatasetSourceType = Literal["deliverable", "recipe"]

DEFAULT_MIN_SCORE = 0.8
MAX_FIELD_CHARS = 16_000
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(api[_-]?key|secret|password|bearer|token)\s*[:=]\s*\S+"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"(?i)-----BEGIN [A-Z ]+ PRIVATE KEY-----"),
)


class VerifiedDatasetRowOut(BaseModel):
    """One Alpaca-compatible training row."""

    model_config = ConfigDict(extra="forbid")

    instruction: str
    input: str
    output: str
    source_type: VerifiedDatasetSourceType
    source_id: str
    source_label: str = ""
    critic_score: float | None = None


class VerifiedDatasetSnapshotOut(BaseModel):
    """Operator snapshot for verified dataset export lane."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    min_score: float
    min_score_label: str
    deliverable_candidates: int = 0
    recipe_candidates: int = 0
    exportable_rows: int = 0
    max_rows: int
    operator_hint: str = ""


class VerifiedDatasetPreviewOut(BaseModel):
    """Preview sample rows before JSONL download."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    total_rows: int = 0
    sample_rows: list[VerifiedDatasetRowOut] = Field(default_factory=list)
    message: str = ""


def min_score_to_five_scale(score: float) -> str:
    """Format 0–1 rubric score as x.x/5."""

    return f"{score * 5.0:.1f}/5"


def _clamp_text(text: str, *, limit: int = MAX_FIELD_CHARS) -> str:
    """Truncate and strip whitespace from export fields."""

    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 3]}..."


def redact_secrets(text: str) -> str:
    """Remove obvious secret patterns before dataset export."""

    out = text
    for pattern in _SECRET_PATTERNS:
        out = pattern.sub("[REDACTED]", out)
    return out


def _score_from_structured(structured: dict[str, Any]) -> float | None:
    """Read critic rubric score (0–1) from deliverable structured JSON."""

    for key in ("critic_rubric_score", "loop_last_rubric_score"):
        raw = structured.get(key)
        if isinstance(raw, (int, float)):
            val = float(raw)
            return val if val <= 1.0 else val / 5.0
    raw_five = structured.get("critic_score_5")
    if isinstance(raw_five, (int, float)):
        return max(0.0, min(float(raw_five) / 5.0, 1.0))
    return None


async def _score_for_deliverable(
    session: AsyncSession,
    *,
    row: TaskFinalDeliverable,
) -> float | None:
    """Resolve critic score from structured payload or linked supervisor session."""

    structured = row.structured_json if isinstance(row.structured_json, dict) else {}
    score = _score_from_structured(structured)
    if score is not None:
        return score

    session_id = row.ballroom_session_id
    if session_id is None:
        return None

    sup = await session.get(SupervisorSession, session_id)
    if sup is None:
        return None
    summary = sup.context_summary if isinstance(sup.context_summary, dict) else {}
    return last_rubric_score_from_summary(summary)


async def _session_goal_for_deliverable(
    session: AsyncSession,
    *,
    row: TaskFinalDeliverable,
) -> str:
    """Build input context from session goal or structured brief."""

    structured = row.structured_json if isinstance(row.structured_json, dict) else {}
    for key in ("business_question", "question", "goal", "brief"):
        raw = structured.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()

    session_id = row.ballroom_session_id
    if session_id is None:
        return row.title

    sup = await session.get(SupervisorSession, session_id)
    if sup is None or not sup.goal.strip():
        return row.title
    return sup.goal.strip()


def _recipe_steps_text(recipe: Recipe) -> str:
    """Flatten verified recipe workflow steps for training input."""

    steps = list((recipe.workflow_template or {}).get("steps") or [])
    lines: list[str] = []
    for idx, step in enumerate(steps[:16], start=1):
        if not isinstance(step, dict):
            continue
        desc = str(step.get("description") or step.get("name") or f"Step {idx}").strip()
        role = str(step.get("agent_role") or step.get("role") or "supervisor").strip()
        lines.append(f"{idx}. [{role}] {desc}")
    if not lines:
        return "Follow verified supervisor session with simulate-first critic gate."
    return "\n".join(lines)


def deliverable_to_alpaca_row(
    *,
    row: TaskFinalDeliverable,
    goal: str,
    critic_score: float | None,
) -> VerifiedDatasetRowOut:
    """Map critic-approved deliverable to Alpaca JSONL row."""

    instruction = (
        "You are a Queenswarm operator assistant. Produce a verified, simulation-gated "
        "deliverable for the operator goal below. Cite sources; no live actions without approval."
    )
    inp = redact_secrets(_clamp_text(goal))
    out = redact_secrets(_clamp_text(row.markdown_body))
    return VerifiedDatasetRowOut(
        instruction=instruction,
        input=inp,
        output=out,
        source_type="deliverable",
        source_id=str(row.id),
        source_label=row.title,
        critic_score=critic_score,
    )


def recipe_to_alpaca_row(recipe: Recipe) -> VerifiedDatasetRowOut:
    """Map verified recipe to Alpaca workflow row."""

    instruction = (
        "You are a Queenswarm supervisor. Execute this verified workflow with simulate-first "
        "guardrails and critic APPROVE before any external publish."
    )
    inp = redact_secrets(
        _clamp_text(
            "\n".join(
                [
                    f"Workflow: {recipe.name}",
                    (recipe.description or "").strip(),
                    "",
                    "Steps:",
                    _recipe_steps_text(recipe),
                ],
            ).strip(),
        ),
    )
    out = redact_secrets(
        _clamp_text(
            f"Completed verified workflow `{recipe.name}` with critic APPROVE, "
            f"success_rate={recipe.success_rate:.0%}, pollen_avg={recipe.avg_pollen_earned:.1f}."
        ),
    )
    return VerifiedDatasetRowOut(
        instruction=instruction,
        input=inp,
        output=out,
        source_type="recipe",
        source_id=str(recipe.id),
        source_label=recipe.name,
        critic_score=1.0,
    )


async def collect_verified_dataset_rows(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    min_score: float | None = None,
    max_rows: int | None = None,
) -> list[VerifiedDatasetRowOut]:
    """Gather Alpaca rows from critic-approved deliverables and verified recipes."""

    threshold = DEFAULT_MIN_SCORE if min_score is None else max(0.0, min(float(min_score), 1.0))
    cap = max_rows if max_rows is not None else settings.verified_dataset_export_max_rows
    cap = max(1, min(int(cap), 2_000))

    deliverable_stmt = (
        select(TaskFinalDeliverable)
        .where(TaskFinalDeliverable.dashboard_user_id == dashboard_user_id)
        .order_by(TaskFinalDeliverable.created_at.desc())
        .limit(min(cap * 4, 800))
    )
    deliverable_rows = list((await session.scalars(deliverable_stmt)).all())

    rows: list[VerifiedDatasetRowOut] = []
    for item in deliverable_rows:
        if len(rows) >= cap:
            break
        score = await _score_for_deliverable(session, row=item)
        if score is None or score < threshold:
            continue
        if not item.markdown_body.strip():
            continue
        goal = await _session_goal_for_deliverable(session, row=item)
        rows.append(
            deliverable_to_alpaca_row(row=item, goal=goal, critic_score=score),
        )

    recipe_stmt = (
        select(Recipe)
        .where(
            Recipe.verified_at.is_not(None),
            Recipe.is_deprecated.is_(False),
        )
        .order_by(Recipe.success_count.desc(), Recipe.updated_at.desc())
        .limit(min(80, cap))
    )
    recipe_rows = list((await session.scalars(recipe_stmt)).all())
    for recipe in recipe_rows:
        if len(rows) >= cap:
            break
        rows.append(recipe_to_alpaca_row(recipe))

    _logger.info(
        "verified_dataset_export.collected",
        dashboard_user_id=str(dashboard_user_id),
        row_count=len(rows),
        min_score=threshold,
    )
    return rows


async def compose_verified_dataset_snapshot(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
) -> VerifiedDatasetSnapshotOut:
    """Return export lane counts for Settings UI."""

    enabled = settings.local_llm_enabled and settings.verified_dataset_export_enabled
    threshold = settings.verified_dataset_export_min_score
    cap = settings.verified_dataset_export_max_rows

    deliverable_stmt = (
        select(TaskFinalDeliverable)
        .where(TaskFinalDeliverable.dashboard_user_id == dashboard_user_id)
        .order_by(TaskFinalDeliverable.created_at.desc())
        .limit(min(cap * 4, 800))
    )
    deliverable_rows = list((await session.scalars(deliverable_stmt)).all())
    deliverable_candidates = 0
    for item in deliverable_rows:
        score = await _score_for_deliverable(session, row=item)
        if score is not None and score >= threshold and item.markdown_body.strip():
            deliverable_candidates += 1

    recipe_count = int(
        await session.scalar(
            select(func.count())
            .select_from(Recipe)
            .where(
                Recipe.verified_at.is_not(None),
                Recipe.is_deprecated.is_(False),
            ),
        )
        or 0,
    )
    recipe_candidates = min(recipe_count, 80)

    exportable = min(deliverable_candidates + recipe_candidates, cap)
    hint = (
        "Export critic-approved deliverables and verified recipes as Alpaca JSONL for Unsloth fine-tune."
        if enabled
        else "Enable LOCAL_LLM_ENABLED and verified_dataset_export to use this lane."
    )
    return VerifiedDatasetSnapshotOut(
        enabled=enabled,
        min_score=threshold,
        min_score_label=min_score_to_five_scale(threshold),
        deliverable_candidates=deliverable_candidates,
        recipe_candidates=recipe_candidates,
        exportable_rows=exportable,
        max_rows=cap,
        operator_hint=hint,
    )


async def compose_verified_dataset_preview(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    sample_limit: int = 5,
) -> VerifiedDatasetPreviewOut:
    """Return first N export rows for operator preview."""

    if not settings.local_llm_enabled or not settings.verified_dataset_export_enabled:
        return VerifiedDatasetPreviewOut(
            ok=False,
            message="Verified dataset export disabled on this deployment.",
        )

    rows = await collect_verified_dataset_rows(session, dashboard_user_id=dashboard_user_id)
    if not rows:
        return VerifiedDatasetPreviewOut(
            ok=True,
            total_rows=0,
            message="No critic-approved rows yet — run closed review loop (≥4/5) on sessions first.",
        )
    limit = max(1, min(int(sample_limit), 20))
    return VerifiedDatasetPreviewOut(
        ok=True,
        total_rows=len(rows),
        sample_rows=rows[:limit],
        message=f"{len(rows)} row(s) ready for Alpaca JSONL export.",
    )


def build_verified_dataset_jsonl_bytes(rows: list[VerifiedDatasetRowOut]) -> bytes:
    """Serialize Alpaca rows to JSONL (instruction/input/output only)."""

    lines: list[str] = []
    for row in rows:
        payload = {
            "instruction": row.instruction,
            "input": row.input,
            "output": row.output,
        }
        lines.append(json.dumps(payload, ensure_ascii=False))
    body = "\n".join(lines)
    if body:
        body += "\n"
    return body.encode("utf-8")


async def export_verified_dataset_jsonl_bytes(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
) -> tuple[bytes, int]:
    """Build full JSONL export blob and row count."""

    rows = await collect_verified_dataset_rows(session, dashboard_user_id=dashboard_user_id)
    return build_verified_dataset_jsonl_bytes(rows), len(rows)


def export_filename(*, dashboard_user_id: uuid.UUID) -> str:
    """Deterministic download filename for operator export."""

    stamp = datetime.now(tz=UTC).strftime("%Y%m%d")
    tail = str(dashboard_user_id).replace("-", "")[-8:]
    return f"queenswarm-verified-dataset-{stamp}-{tail}.jsonl"


__all__ = [
    "VerifiedDatasetPreviewOut",
    "VerifiedDatasetRowOut",
    "VerifiedDatasetSnapshotOut",
    "build_verified_dataset_jsonl_bytes",
    "collect_verified_dataset_rows",
    "compose_verified_dataset_preview",
    "compose_verified_dataset_snapshot",
    "deliverable_to_alpaca_row",
    "export_filename",
    "export_verified_dataset_jsonl_bytes",
    "min_score_to_five_scale",
    "recipe_to_alpaca_row",
    "redact_secrets",
]
