"""Track L DA10 — Analytics report critic closed loop (LOOP5 preset, rubric ≥4/5)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.analytics_data_lineage_service import (
    _resolve_analytics_row,
    build_lineage_rows_from_deliverable,
)
from app.application.services.analytics_export_lane_service import (
    CRITIC_MIN_SCORE,
    _resolve_critic_score,
)
from app.application.services.analytics_report_artifact_service import _merge_tags
from app.application.services.analytics_workspace_deliverable_utils import (
    ANALYTICS_REPORT_FORMAT,
    parse_chart_blocks,
)
from app.application.services.closed_loop_presets_service import get_closed_loop_preset
from app.application.services.closed_review_loop_service import (
    ClosedReviewLoopResultOut,
    ClosedReviewLoopRunIn,
    run_closed_review_loop,
)
from app.application.services.loop_guardrails_service import min_score_to_five_scale
from app.core.config import settings
from app.core.logging import get_logger
from app.domain.outputs.service import persist_final_deliverable

_logger = get_logger(__name__)

ANALYTICS_CRITIC_PRESET_ID = "analytics_report"
ANALYTICS_CRITIC_RUBRIC_ID = "business-analytics-report"


class AnalyticsReportCriticSnapshotOut(BaseModel):
    """Operator snapshot for report critic closed loop."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    has_artifact: bool
    deliverable_id: str | None = None
    report_title: str | None = None
    preset_id: str = ANALYTICS_CRITIC_PRESET_ID
    preset_label: str = ""
    rubric_template_id: str = ANALYTICS_CRITIC_RUBRIC_ID
    min_score: float = CRITIC_MIN_SCORE
    min_score_label: str = min_score_to_five_scale(CRITIC_MIN_SCORE)
    critic_score: float | None = None
    critic_score_label: str | None = None
    critic_passed: bool = False
    export_ready: bool = False
    last_run_at: str | None = None
    turns_used: int | None = None
    operator_hint: str = ""


class AnalyticsReportCriticRunIn(BaseModel):
    """Optional scope for critic loop run."""

    model_config = ConfigDict(extra="forbid")

    deliverable_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None


class AnalyticsReportCriticRunOut(BaseModel):
    """Outcome of analytics report critic closed loop."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    passed: bool
    deliverable_id: str | None = None
    report_title: str | None = None
    critic_score: float | None = None
    critic_score_label: str | None = None
    export_ready: bool = False
    turns_used: int = 0
    max_turns: int = 0
    message: str = ""
    loop: ClosedReviewLoopResultOut | None = None


def _compose_critic_text(*, markdown_body: str, lineage_rows: list[Any]) -> str:
    """Build rubric input — narrative plus lineage appendix for citation scoring."""

    lines = [markdown_body.strip()]
    if lineage_rows:
        lines.append("\n\n--- Data lineage ---\n")
        for item in lineage_rows[:24]:
            if hasattr(item, "section_label"):
                lines.append(
                    f"- {item.section_label}: {item.connector_label} · {item.query} · {item.fetched_at}",
                )
            elif isinstance(item, dict):
                lines.append(
                    f"- {item.get('section_label')}: {item.get('connector_label')} · "
                    f"{item.get('query')} · {item.get('fetched_at')}",
                )
    return "\n".join(lines).strip()[:12_000]


async def compose_analytics_report_critic_snapshot(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    task_id: uuid.UUID | None = None,
    deliverable_id: uuid.UUID | None = None,
) -> AnalyticsReportCriticSnapshotOut:
    """Return critic gate status for active analytics report artifact."""

    preset = get_closed_loop_preset(ANALYTICS_CRITIC_PRESET_ID)
    preset_label = preset.label if preset is not None else "Analytics report critic loop"
    min_score = preset.min_score if preset is not None else CRITIC_MIN_SCORE

    if not settings.analytics_report_critic_enabled:
        return AnalyticsReportCriticSnapshotOut(
            enabled=False,
            has_artifact=False,
            preset_label=preset_label,
            min_score=min_score,
            min_score_label=min_score_to_five_scale(min_score),
            operator_hint="Analytics report critic loop disabled.",
        )

    row = await _resolve_analytics_row(
        session,
        dashboard_user_id=dashboard_user_id,
        task_id=task_id,
        deliverable_id=deliverable_id,
    )
    if row is None:
        return AnalyticsReportCriticSnapshotOut(
            enabled=True,
            has_artifact=False,
            preset_label=preset_label,
            min_score=min_score,
            min_score_label=min_score_to_five_scale(min_score),
            operator_hint=(
                "No analytics report artifact — dispatch a business question and wait for narrative bee."
            ),
        )

    structured = dict(row.structured_json) if isinstance(row.structured_json, dict) else {}
    critic_score = await _resolve_critic_score(
        session,
        structured=structured,
        task_id=row.source_task_id,
    )
    critic_passed = critic_score is not None and critic_score >= min_score
    export_ready = critic_passed and len(row.markdown_body.strip()) >= 20
    last_run_at = structured.get("critic_run_at")
    turns_used_raw = structured.get("critic_turns_used")

    hint_parts: list[str] = []
    if critic_passed:
        hint_parts.append(
            f"Critic PASS — {min_score_to_five_scale(critic_score)} ≥ {min_score_to_five_scale(min_score)}. "
            "Export lane unlocked (simulate-first).",
        )
    elif critic_score is not None:
        hint_parts.append(
            f"Critic {min_score_to_five_scale(critic_score)} — run closed loop to reach "
            f"≥{min_score_to_five_scale(min_score)} before export.",
        )
    else:
        hint_parts.append(
            f"No critic score yet — run LOOP5 preset ({preset_label}) before staging export.",
        )

    _logger.info(
        "analytics_report_critic.snapshot",
        agent_id="analytics_report_critic",
        swarm_id=str(dashboard_user_id),
        deliverable_id=str(row.id),
        critic_passed=critic_passed,
    )

    return AnalyticsReportCriticSnapshotOut(
        enabled=True,
        has_artifact=True,
        deliverable_id=str(row.id),
        report_title=row.title,
        preset_label=preset_label,
        min_score=min_score,
        min_score_label=min_score_to_five_scale(min_score),
        critic_score=critic_score,
        critic_score_label=min_score_to_five_scale(critic_score) if critic_score is not None else None,
        critic_passed=critic_passed,
        export_ready=export_ready,
        last_run_at=str(last_run_at) if last_run_at else None,
        turns_used=int(turns_used_raw) if isinstance(turns_used_raw, int) else None,
        operator_hint=" ".join(hint_parts),
    )


async def run_analytics_report_critic_loop(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    body: AnalyticsReportCriticRunIn,
) -> AnalyticsReportCriticRunOut:
    """Run LOOP5 analytics report critic — persist score + optional revised markdown."""

    if not settings.analytics_report_critic_enabled:
        raise ValueError("analytics_report_critic_disabled")

    preset = get_closed_loop_preset(ANALYTICS_CRITIC_PRESET_ID)
    if preset is None:
        raise ValueError("analytics_report_critic_preset_unavailable")

    row = await _resolve_analytics_row(
        session,
        dashboard_user_id=dashboard_user_id,
        task_id=body.task_id,
        deliverable_id=body.deliverable_id,
    )
    if row is None:
        return AnalyticsReportCriticRunOut(
            ok=False,
            passed=False,
            message="No analytics report artifact — complete Question wizard dispatch first.",
        )

    lineage_rows = build_lineage_rows_from_deliverable(row)
    critic_text = _compose_critic_text(markdown_body=row.markdown_body, lineage_rows=lineage_rows)

    loop_result = await run_closed_review_loop(
        session,
        tenant_id=tenant_id,
        body=ClosedReviewLoopRunIn(
            text=critic_text,
            template_id=preset.rubric_template_id,
            max_turns=preset.max_turns,
            min_score=preset.min_score,
            task_id="analytics_report_critic_loop5",
        ),
    )

    last_score = loop_result.iterations[-1].score if loop_result.iterations else None
    structured = dict(row.structured_json) if isinstance(row.structured_json, dict) else {}
    structured["format"] = ANALYTICS_REPORT_FORMAT
    structured["critic_preset_id"] = preset.preset_id
    structured["critic_rubric_template_id"] = preset.rubric_template_id
    structured["critic_run_at"] = datetime.now(tz=UTC).isoformat()
    structured["critic_turns_used"] = loop_result.turns_used
    if last_score is not None:
        structured["critic_rubric_score"] = last_score
        structured["loop_last_rubric_score"] = last_score
    if loop_result.iterations:
        structured["critic_feedback"] = loop_result.iterations[-1].feedback[:4000]

    markdown_body = row.markdown_body
    if loop_result.passed and loop_result.final_text.strip() != critic_text.strip():
        revised = loop_result.final_text.strip()
        if revised.startswith("#") or len(revised) >= 20:
            markdown_body = revised.split("\n\n--- Data lineage ---")[0].strip() or revised

    tags = row.tags if isinstance(row.tags, list) else []
    safe_tags = [str(t) for t in tags]

    saved = await persist_final_deliverable(
        session,
        lineage_id=row.lineage_id,
        dashboard_user_id=dashboard_user_id,
        ballroom_session_id=row.ballroom_session_id,
        mission_id=row.mission_id,
        source_task_id=row.source_task_id,
        slug_hint=row.slug,
        title_hint=row.title,
        markdown_body=markdown_body,
        structured=structured,
        tags=_merge_tags(safe_tags),
        voice_script=row.voice_script,
    )
    await session.flush()

    export_ready = loop_result.passed and len(markdown_body.strip()) >= 20
    score_label = min_score_to_five_scale(last_score) if last_score is not None else None

    _logger.info(
        "analytics_report_critic.run",
        agent_id="analytics_report_critic",
        swarm_id=str(tenant_id),
        task_id="analytics_report_critic_loop5",
        deliverable_id=str(saved.id),
        passed=loop_result.passed,
        score=last_score,
        turns=loop_result.turns_used,
    )

    message = loop_result.message or (
        f"Critic PASS — {score_label} (export ready)."
        if loop_result.passed
        else f"Critic below floor — {score_label or 'n/a'} vs {min_score_to_five_scale(preset.min_score)}."
    )

    return AnalyticsReportCriticRunOut(
        ok=True,
        passed=loop_result.passed,
        deliverable_id=str(saved.id),
        report_title=saved.title,
        critic_score=last_score,
        critic_score_label=score_label,
        export_ready=export_ready,
        turns_used=loop_result.turns_used,
        max_turns=loop_result.max_turns,
        message=message,
        loop=loop_result,
    )


__all__ = [
    "ANALYTICS_CRITIC_PRESET_ID",
    "ANALYTICS_CRITIC_RUBRIC_ID",
    "AnalyticsReportCriticRunIn",
    "AnalyticsReportCriticRunOut",
    "AnalyticsReportCriticSnapshotOut",
    "compose_analytics_report_critic_snapshot",
    "run_analytics_report_critic_loop",
]
