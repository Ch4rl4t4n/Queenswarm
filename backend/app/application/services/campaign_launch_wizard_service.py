"""NP6 — Campaign launch wizard: brand pack → draft → rubric → simulate publish."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.curated_memory_service import CuratedMemoryService
from app.application.services.brand_context_pack_service import is_brand_pack_ready
from app.application.services.publish_pack import (
    PublishChannel,
    PublishPackArtifact,
    archive_verified_publish_pack,
)
from app.application.services.publish_queue import classify_publish_queue_status, review_publish_queue_item
from app.application.services.rubric_templates import evaluate_text_with_rubric, get_rubric_template
from app.application.services.social_publish import run_social_publish
from app.core.config import settings
from app.core.logging import get_logger
from app.domain.memory.curated import CuratedFileKind
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

CAMPAIGN_LAUNCH_WIZARD_SETTINGS_KEY = "campaign_launch_wizard"
DEFAULT_RUBRIC_TEMPLATE_ID = "marketing-creative"
MIN_DRAFT_BODY_CHARS = 20
MIN_DRAFT_TITLE_CHARS = 3
MIN_CURATED_BRAND_CHARS = 40

CampaignStepId = Literal["brand_pack", "draft_copy", "rubric_score", "simulate_publish"]
CampaignStepStatus = Literal["done", "ready", "pending", "blocked"]


class CampaignBrandPackOut(BaseModel):
    """Selectable brand context pack for marketing copy."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    source: Literal["builtin", "tenant"]
    detail: str
    ready: bool = True


class CampaignLaunchStepOut(BaseModel):
    """One checklist row in the 4-step wizard."""

    model_config = ConfigDict(extra="ignore")

    id: CampaignStepId
    label: str
    status: CampaignStepStatus
    detail: str
    link: str | None = None


class CampaignLaunchDraftOut(BaseModel):
    """Operator draft copy persisted in tenant settings."""

    model_config = ConfigDict(extra="ignore")

    brand_pack_id: str | None = None
    channel: PublishChannel = "instagram"
    title: str = ""
    body: str = ""
    cta: str = ""
    hashtags: list[str] = Field(default_factory=list)
    media_url: str | None = None


class CampaignLaunchRubricOut(BaseModel):
    """Last rubric evaluation for the draft."""

    model_config = ConfigDict(extra="ignore")

    template_id: str = DEFAULT_RUBRIC_TEMPLATE_ID
    template_name: str = ""
    score: float | None = None
    pass_threshold: float = 0.75
    passed: bool = False
    feedback: str = ""
    evaluated_at: datetime | None = None


class CampaignLaunchWizardSnapshotOut(BaseModel):
    """Single snapshot for Marketing campaign launch wizard."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    progress_pct: int = Field(ge=0, le=100)
    steps: list[CampaignLaunchStepOut] = Field(default_factory=list)
    brand_packs: list[CampaignBrandPackOut] = Field(default_factory=list)
    draft: CampaignLaunchDraftOut = Field(default_factory=CampaignLaunchDraftOut)
    rubric: CampaignLaunchRubricOut = Field(default_factory=CampaignLaunchRubricOut)
    deliverable_id: str | None = None
    simulate_ok: bool | None = None
    simulate_message: str = ""
    links: dict[str, str] = Field(default_factory=dict)


class CampaignLaunchDraftPatchIn(BaseModel):
    """PATCH body for wizard draft fields."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    brand_pack_id: str | None = Field(default=None, max_length=64)
    channel: PublishChannel | None = None
    title: str | None = Field(default=None, max_length=200)
    body: str | None = Field(default=None, max_length=8000)
    cta: str | None = Field(default=None, max_length=200)
    hashtags: list[str] | None = Field(default=None, max_length=20)
    media_url: str | None = Field(default=None, max_length=500)


class CampaignLaunchRubricRunIn(BaseModel):
    """Optional overrides when scoring draft copy."""

    model_config = ConfigDict(extra="forbid")

    template_id: str = Field(default=DEFAULT_RUBRIC_TEMPLATE_ID, min_length=2, max_length=64)


class CampaignLaunchRubricRunOut(BaseModel):
    """Rubric scoring result persisted to tenant wizard state."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    passed: bool
    score: float
    pass_threshold: float
    template_id: str
    template_name: str
    feedback: str = ""
    message: str = ""


class CampaignLaunchSubmitOut(BaseModel):
    """Archive publish pack, approve queue, and simulate social publish."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    deliverable_id: str
    queue_status: str
    simulate_ok: bool
    simulate_message: str = ""
    publish_queue_href: str = "/apps-tools/marketing-team?section=queue#publish-queue"
    social_publish_href: str = "/apps-tools/marketing-team?section=publish#social-publish"
    message: str = ""


_BUILTIN_BRAND_PACKS: tuple[CampaignBrandPackOut, ...] = (
    CampaignBrandPackOut(
        id="queenswarm-default",
        label="Queenswarm default",
        source="builtin",
        detail="Pollen amber voice · simulate-first · no fabricated stats.",
        ready=True,
    ),
)


def _default_links() -> dict[str, str]:
    return {
        "brain_pack": "/knowledge?tab=memory#brain-pack",
        "publish_queue": "/apps-tools/marketing-team?section=queue#publish-queue",
        "social_publish": "/apps-tools/marketing-team?section=publish#social-publish",
        "closed_review_loop": "/settings?tab=harness#harness-closed-review-loop",
    }


def _load_wizard_bucket(tenant: Tenant | None) -> dict[str, Any]:
    if tenant is None:
        return {}
    root = dict(tenant.operator_settings or {})
    raw = root.get(CAMPAIGN_LAUNCH_WIZARD_SETTINGS_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def _draft_from_bucket(bucket: dict[str, Any]) -> CampaignLaunchDraftOut:
    hashtags_raw = bucket.get("hashtags")
    hashtags = [str(tag).strip().lstrip("#") for tag in hashtags_raw][:20] if isinstance(hashtags_raw, list) else []
    channel = str(bucket.get("channel") or "instagram").strip().lower() or "instagram"
    media = str(bucket.get("media_url") or "").strip() or None
    return CampaignLaunchDraftOut(
        brand_pack_id=str(bucket.get("brand_pack_id") or "").strip() or None,
        channel=channel,  # type: ignore[arg-type]
        title=str(bucket.get("title") or "").strip(),
        body=str(bucket.get("body") or "").strip(),
        cta=str(bucket.get("cta") or "").strip(),
        hashtags=hashtags,
        media_url=media,
    )


def _rubric_from_bucket(bucket: dict[str, Any]) -> CampaignLaunchRubricOut:
    template_id = str(bucket.get("rubric_template_id") or DEFAULT_RUBRIC_TEMPLATE_ID)
    template = get_rubric_template(template_id)
    score_raw = bucket.get("rubric_score")
    score = float(score_raw) if isinstance(score_raw, (int, float)) else None
    evaluated_at_raw = bucket.get("rubric_evaluated_at")
    evaluated_at: datetime | None = None
    if isinstance(evaluated_at_raw, str) and evaluated_at_raw.strip():
        try:
            evaluated_at = datetime.fromisoformat(evaluated_at_raw.replace("Z", "+00:00"))
        except ValueError:
            evaluated_at = None
    threshold = template.pass_threshold if template is not None else 0.75
    return CampaignLaunchRubricOut(
        template_id=template_id,
        template_name=template.name if template is not None else template_id,
        score=score,
        pass_threshold=threshold,
        passed=bool(bucket.get("rubric_passed")),
        feedback=str(bucket.get("rubric_feedback") or "").strip()[:2000],
        evaluated_at=evaluated_at,
    )


async def _compose_brand_packs(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> list[CampaignBrandPackOut]:
    """Return builtin + tenant curated brand packs."""

    packs = list(_BUILTIN_BRAND_PACKS)
    memory = CuratedMemoryService(db=session)
    bundle = await memory.get_bundle(tenant_id)
    brand_md = (bundle.get(CuratedFileKind.BRAND) or "").strip()
    brand_ready = is_brand_pack_ready(brand_md)
    packs.append(
        CampaignBrandPackOut(
            id="curated-brand",
            label="Brain Pack brand context",
            source="tenant",
            detail=(
                f"NP3 Brand tab — voice, forbidden claims, examples ({len(brand_md)} chars)."
                if brand_ready
                else "Fill Brand tab: voice bullets, forbidden claims, example posts."
            ),
            ready=brand_ready,
        ),
    )
    return packs


def _brand_pack_step(
    *,
    draft: CampaignLaunchDraftOut,
    brand_packs: list[CampaignBrandPackOut],
) -> CampaignLaunchStepOut:
    pack_id = draft.brand_pack_id
    if not pack_id:
        return CampaignLaunchStepOut(
            id="brand_pack",
            label="Pick brand pack",
            status="pending",
            detail="Select Queenswarm default or Brain Pack brand voice.",
            link="/knowledge?tab=memory#brain-pack-brand",
        )
    selected = next((row for row in brand_packs if row.id == pack_id), None)
    if selected is None:
        return CampaignLaunchStepOut(
            id="brand_pack",
            label="Pick brand pack",
            status="blocked",
            detail=f"Unknown brand pack: {pack_id}",
        )
    if not selected.ready:
        return CampaignLaunchStepOut(
            id="brand_pack",
            label="Pick brand pack",
            status="blocked",
            detail=selected.detail,
            link="/knowledge?tab=memory#brain-pack-brand",
        )
    return CampaignLaunchStepOut(
        id="brand_pack",
        label="Pick brand pack",
        status="done",
        detail=f"{selected.label} selected.",
    )


def _draft_copy_step(*, draft: CampaignLaunchDraftOut) -> CampaignLaunchStepOut:
    title_ok = len(draft.title.strip()) >= MIN_DRAFT_TITLE_CHARS
    body_ok = len(draft.body.strip()) >= MIN_DRAFT_BODY_CHARS
    cta_ok = len(draft.cta.strip()) >= 2
    if title_ok and body_ok and cta_ok:
        return CampaignLaunchStepOut(
            id="draft_copy",
            label="Draft copy",
            status="done",
            detail=f"{draft.channel} · {len(draft.body)} chars · CTA ready.",
        )
    missing: list[str] = []
    if not title_ok:
        missing.append(f"title ≥{MIN_DRAFT_TITLE_CHARS} chars")
    if not body_ok:
        missing.append(f"body ≥{MIN_DRAFT_BODY_CHARS} chars")
    if not cta_ok:
        missing.append("CTA ≥2 chars")
    return CampaignLaunchStepOut(
        id="draft_copy",
        label="Draft copy",
        status="ready" if draft.body.strip() else "pending",
        detail=f"Need: {', '.join(missing)}.",
    )


def _rubric_step(*, rubric: CampaignLaunchRubricOut) -> CampaignLaunchStepOut:
    if rubric.passed and rubric.score is not None:
        return CampaignLaunchStepOut(
            id="rubric_score",
            label="Rubric score",
            status="done",
            detail=f"{rubric.template_name} {rubric.score:.0%} ≥ {rubric.pass_threshold:.0%}.",
            link="/settings?tab=harness#harness-closed-review-loop",
        )
    if rubric.score is not None:
        return CampaignLaunchStepOut(
            id="rubric_score",
            label="Rubric score",
            status="blocked",
            detail=(
                f"Score {rubric.score:.0%} below {rubric.pass_threshold:.0%} — "
                "revise copy or run Closed Review Loop."
            ),
            link="/settings?tab=harness#harness-closed-review-loop",
        )
    return CampaignLaunchStepOut(
        id="rubric_score",
        label="Rubric score",
        status="pending",
        detail=f"Run {DEFAULT_RUBRIC_TEMPLATE_ID} rubric on draft (≥75%).",
    )


def _simulate_step(
    *,
    bucket: dict[str, Any],
    deliverable_id: str | None,
) -> CampaignLaunchStepOut:
    if bool(bucket.get("simulate_completed")):
        msg = str(bucket.get("simulate_message") or "Simulate publish completed.")
        return CampaignLaunchStepOut(
            id="simulate_publish",
            label="Simulate publish",
            status="done",
            detail=msg[:280],
            link="/apps-tools/marketing-team?section=publish#social-publish",
        )
    if deliverable_id and not bool(bucket.get("simulate_completed")):
        sim_msg = str(bucket.get("simulate_message") or "").strip()
        detail = sim_msg or "Pack archived — connect OAuth and run Social Simulate."
        return CampaignLaunchStepOut(
            id="simulate_publish",
            label="Simulate publish",
            status="ready",
            detail=detail[:280],
            link="/apps-tools/marketing-team?section=publish#social-publish",
        )
    return CampaignLaunchStepOut(
        id="simulate_publish",
        label="Simulate publish",
        status="pending",
        detail="Submit wizard to archive pack, approve queue, and simulate.",
        link="/integrations?tab=studio&section=publish#social-publish",
    )


def _progress_pct(steps: list[CampaignLaunchStepOut]) -> int:
    if not steps:
        return 0
    done = sum(1 for step in steps if step.status == "done")
    return int(round(done / len(steps) * 100))


async def _save_wizard_bucket(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    bucket: dict[str, Any],
) -> None:
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        msg = f"Tenant {tenant_id} not found"
        raise ValueError(msg)
    root = dict(tenant.operator_settings or {})
    bucket["updated_at"] = datetime.now(tz=UTC).isoformat()
    root[CAMPAIGN_LAUNCH_WIZARD_SETTINGS_KEY] = bucket
    tenant.operator_settings = root
    await session.flush()


def _compose_draft_text(*, draft: CampaignLaunchDraftOut) -> str:
    tags = " ".join(f"#{tag}" for tag in draft.hashtags[:12])
    parts = [draft.title.strip(), draft.body.strip()]
    if draft.cta.strip():
        parts.append(f"CTA: {draft.cta.strip()}")
    if tags:
        parts.append(tags)
    return "\n\n".join(part for part in parts if part)


def _score_from_evaluation(evaluation: dict[str, Any]) -> float:
    raw = evaluation.get("confidence")
    if isinstance(raw, (int, float)):
        return max(0.0, min(float(raw), 1.0))
    return 1.0 if bool(evaluation.get("is_valid")) else 0.0


def _evaluation_passed(*, evaluation: dict[str, Any], threshold: float) -> bool:
    score = _score_from_evaluation(evaluation)
    floor = max(threshold, float(evaluation.get("pass_threshold") or threshold))
    return bool(evaluation.get("is_valid")) and score >= floor


async def compose_campaign_launch_wizard_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> CampaignLaunchWizardSnapshotOut:
    """Build 4-step checklist snapshot with brand packs and draft state."""

    if not settings.campaign_launch_wizard_enabled:
        return CampaignLaunchWizardSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            progress_pct=0,
            steps=[],
            links=_default_links(),
        )

    tenant = await session.get(Tenant, tenant_id)
    bucket = _load_wizard_bucket(tenant)
    draft = _draft_from_bucket(bucket)
    rubric = _rubric_from_bucket(bucket)
    brand_packs = await _compose_brand_packs(session, tenant_id=tenant_id)
    deliverable_id = str(bucket.get("deliverable_id") or "").strip() or None

    steps = [
        _brand_pack_step(draft=draft, brand_packs=brand_packs),
        _draft_copy_step(draft=draft),
        _rubric_step(rubric=rubric),
        _simulate_step(bucket=bucket, deliverable_id=deliverable_id),
    ]

    simulate_ok: bool | None = None
    if bucket.get("simulate_completed") is not None:
        simulate_ok = bool(bucket.get("simulate_completed"))

    return CampaignLaunchWizardSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        progress_pct=_progress_pct(steps),
        steps=steps,
        brand_packs=brand_packs,
        draft=draft,
        rubric=rubric,
        deliverable_id=deliverable_id,
        simulate_ok=simulate_ok,
        simulate_message=str(bucket.get("simulate_message") or "").strip(),
        links=_default_links(),
    )


async def patch_campaign_launch_wizard_draft(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    patch: CampaignLaunchDraftPatchIn,
) -> CampaignLaunchWizardSnapshotOut:
    """Persist draft fields; reset rubric when copy changes."""

    if not settings.campaign_launch_wizard_enabled:
        raise ValueError("Campaign Launch wizard is disabled.")

    tenant = await session.get(Tenant, tenant_id)
    bucket = _load_wizard_bucket(tenant)
    draft = _draft_from_bucket(bucket)
    copy_changed = False

    data = patch.model_dump(exclude_unset=True)
    if "brand_pack_id" in data:
        bucket["brand_pack_id"] = data["brand_pack_id"]
    if "channel" in data and data["channel"] is not None:
        bucket["channel"] = data["channel"]
    if "title" in data and data["title"] is not None:
        bucket["title"] = data["title"]
        copy_changed = True
    if "body" in data and data["body"] is not None:
        bucket["body"] = data["body"]
        copy_changed = True
    if "cta" in data and data["cta"] is not None:
        bucket["cta"] = data["cta"]
        copy_changed = True
    if "hashtags" in data and data["hashtags"] is not None:
        bucket["hashtags"] = [str(tag).strip().lstrip("#") for tag in data["hashtags"]][:20]
        copy_changed = True
    if "media_url" in data:
        media = str(data["media_url"] or "").strip()
        bucket["media_url"] = media or None

    if copy_changed:
        bucket.pop("rubric_score", None)
        bucket.pop("rubric_passed", None)
        bucket.pop("rubric_feedback", None)
        bucket.pop("rubric_evaluated_at", None)
        bucket.pop("simulate_completed", None)
        bucket.pop("simulate_message", None)
        bucket.pop("deliverable_id", None)

    await _save_wizard_bucket(session, tenant_id=tenant_id, bucket=bucket)
    _logger.info(
        "campaign_launch_wizard.draft_patched",
        agent_id="campaign_launch_wizard",
        swarm_id=str(tenant_id),
        brand_pack_id=draft.brand_pack_id,
        copy_changed=copy_changed,
    )
    return await compose_campaign_launch_wizard_snapshot(session, tenant_id=tenant_id)


async def run_campaign_launch_rubric(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    body: CampaignLaunchRubricRunIn,
) -> CampaignLaunchRubricRunOut:
    """Score current draft with marketing creative rubric."""

    if not settings.campaign_launch_wizard_enabled:
        raise ValueError("Campaign Launch wizard is disabled.")

    template = get_rubric_template(body.template_id)
    if template is None:
        raise ValueError(f"Unknown rubric template: {body.template_id}")

    tenant = await session.get(Tenant, tenant_id)
    bucket = _load_wizard_bucket(tenant)
    draft = _draft_from_bucket(bucket)
    if len(draft.body.strip()) < MIN_DRAFT_BODY_CHARS:
        raise ValueError(f"Draft body must be at least {MIN_DRAFT_BODY_CHARS} characters.")

    text = _compose_draft_text(draft=draft)
    evaluation = await evaluate_text_with_rubric(
        session,
        text=text,
        template_id=body.template_id,
        swarm_id=str(tenant_id),
        task_id="campaign_launch_wizard",
    )
    score = _score_from_evaluation(evaluation)
    passed = _evaluation_passed(evaluation=evaluation, threshold=template.pass_threshold)
    feedback = str(evaluation.get("feedback") or evaluation.get("reasoning") or "").strip()

    bucket["rubric_template_id"] = template.id
    bucket["rubric_score"] = round(score, 4)
    bucket["rubric_passed"] = passed
    bucket["rubric_feedback"] = feedback[:2000]
    bucket["rubric_evaluated_at"] = datetime.now(tz=UTC).isoformat()
    await _save_wizard_bucket(session, tenant_id=tenant_id, bucket=bucket)

    message = (
        f"Rubric pass ({score:.0%} ≥ {template.pass_threshold:.0%})."
        if passed
        else f"Below threshold — {score:.0%} vs {template.pass_threshold:.0%}. Revise copy."
    )
    _logger.info(
        "campaign_launch_wizard.rubric_scored",
        agent_id="campaign_launch_wizard",
        swarm_id=str(tenant_id),
        template_id=template.id,
        score=score,
        passed=passed,
    )
    return CampaignLaunchRubricRunOut(
        ok=True,
        passed=passed,
        score=score,
        pass_threshold=template.pass_threshold,
        template_id=template.id,
        template_name=template.name,
        feedback=feedback[:2000],
        message=message,
    )


async def submit_campaign_launch_wizard(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    created_by_subject: str,
) -> CampaignLaunchSubmitOut:
    """Archive verified publish pack, approve queue, and run social simulate."""

    if not settings.campaign_launch_wizard_enabled:
        raise ValueError("Campaign Launch wizard is disabled.")

    snapshot = await compose_campaign_launch_wizard_snapshot(session, tenant_id=tenant_id)
    pending_steps = [step for step in snapshot.steps if step.status != "done" and step.id != "simulate_publish"]
    if pending_steps:
        labels = ", ".join(step.label for step in pending_steps[:3])
        raise ValueError(f"Complete wizard steps first: {labels}.")

    if not snapshot.rubric.passed:
        raise ValueError("Rubric must pass before submit.")

    tenant = await session.get(Tenant, tenant_id)
    bucket = _load_wizard_bucket(tenant)
    draft = _draft_from_bucket(bucket)

    supervisor = SupervisorSession(
        tenant_id=tenant_id,
        goal="NP6 Campaign launch wizard — verified simulate-only publish pack",
        status="completed",
        runtime_mode="inprocess",
        created_by_subject=created_by_subject,
        context_summary={
            "campaign_launch_wizard": True,
            "brand_pack_id": draft.brand_pack_id,
            "channel": draft.channel,
        },
        started_at=datetime.now(tz=UTC),
        completed_at=datetime.now(tz=UTC),
    )
    session.add(supervisor)
    await session.flush()

    pack = PublishPackArtifact(
        channel=draft.channel,
        title=draft.title.strip(),
        body=draft.body.strip(),
        hashtags=draft.hashtags,
        cta=draft.cta.strip(),
        media_url=draft.media_url,
        simulate_only=True,
    )
    row = await archive_verified_publish_pack(
        session,
        supervisor_session=supervisor,
        pack=pack,
        critic_excerpt=snapshot.rubric.feedback or "Campaign launch wizard rubric pass.",
        verified=True,
    )
    if row is None:
        raise RuntimeError("Failed to archive publish pack.")

    queue_status = classify_publish_queue_status(row) or "pending"
    if queue_status == "pending":
        reviewed = await review_publish_queue_item(
            session,
            deliverable_id=row.id,
            dashboard_user_id=dashboard_user_id,
            decision="approve",
            note="NP6 campaign launch wizard auto-approve",
            reviewed_by=created_by_subject,
        )
        queue_status = reviewed.status

    simulate_ok = False
    simulate_message = ""
    try:
        sim_result = await run_social_publish(
            session,
            deliverable_id=row.id,
            dashboard_user_id=dashboard_user_id,
            tenant=tenant,
            mode="simulate",
            reviewed_by=created_by_subject,
        )
        simulate_ok = bool(sim_result.ok)
        simulate_message = str(sim_result.message or "").strip()
    except (ValueError, LookupError) as exc:
        simulate_message = str(exc)

    bucket["deliverable_id"] = str(row.id)
    bucket["simulate_completed"] = simulate_ok
    bucket["simulate_message"] = simulate_message or (
        "Simulate OK — ready for live when OAuth connected."
        if simulate_ok
        else "Pack approved — connect OAuth in Social publish to simulate."
    )
    await _save_wizard_bucket(session, tenant_id=tenant_id, bucket=bucket)

    _logger.info(
        "campaign_launch_wizard.submitted",
        agent_id="campaign_launch_wizard",
        swarm_id=str(tenant_id),
        deliverable_id=str(row.id),
        simulate_ok=simulate_ok,
        queue_status=queue_status,
    )

    ok = queue_status == "approved"
    message = "Campaign pack archived and queue approved."
    if simulate_ok:
        message = f"{message} Social simulate completed."
    elif simulate_message:
        message = f"{message} {simulate_message}"

    return CampaignLaunchSubmitOut(
        ok=ok,
        deliverable_id=str(row.id),
        queue_status=queue_status,
        simulate_ok=simulate_ok,
        simulate_message=simulate_message,
        message=message,
    )


__all__ = [
    "CAMPAIGN_LAUNCH_WIZARD_SETTINGS_KEY",
    "CampaignLaunchDraftPatchIn",
    "CampaignLaunchRubricRunIn",
    "CampaignLaunchRubricRunOut",
    "CampaignLaunchSubmitOut",
    "CampaignLaunchWizardSnapshotOut",
    "compose_campaign_launch_wizard_snapshot",
    "patch_campaign_launch_wizard_draft",
    "run_campaign_launch_rubric",
    "submit_campaign_launch_wizard",
]
