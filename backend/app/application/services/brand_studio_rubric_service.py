"""POS-I4 — Brand studio rubric preview (simulate-only) for Marketing Team."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.brand_context_pack_service import compose_brand_context_pack_snapshot
from app.application.services.publish_creative_rubric_service import (
    PublishCreativeRubricOut,
    evaluate_publish_pack_creative_rubric,
)
from app.core.config import settings

MIN_PREVIEW_BODY_CHARS = 20


class BrandStudioRubricPreviewIn(BaseModel):
    """Operator copy sample for simulate-only rubric scoring."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(default="", max_length=200)
    body: str = Field(min_length=MIN_PREVIEW_BODY_CHARS, max_length=8000)
    cta: str = Field(default="", max_length=200)
    hashtags: list[str] = Field(default_factory=list, max_length=20)


class BrandStudioSnapshotOut(BaseModel):
    """Brand studio readiness + links — no live publish."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    generated_at: datetime
    simulate_only: bool = True
    brand_ready: bool = False
    brand_char_count: int = 0
    brand_usage_pct: int = 0
    sections_filled: int = 0
    operator_hint: str = ""
    links: dict[str, str] = Field(default_factory=dict)


class BrandStudioRubricPreviewOut(BaseModel):
    """Simulate-only rubric result for Brand studio preview."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    simulate_only: bool = True
    generated_at: datetime
    brand_ready: bool = False
    rubric: PublishCreativeRubricOut
    operator_hint: str = ""


async def compose_brand_studio_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> BrandStudioSnapshotOut:
    """Return brand pack readiness for Marketing Team Brand studio tab."""

    now = datetime.now(tz=UTC)
    if not settings.brand_studio_rubric_preview_enabled or not settings.marketing_team_enabled:
        return BrandStudioSnapshotOut(
            enabled=False,
            generated_at=now,
            operator_hint="Brand studio rubric preview disabled.",
        )

    brand = await compose_brand_context_pack_snapshot(session, tenant_id=tenant_id)
    sections_filled = sum(1 for row in brand.sections if row.filled)

    hint = "Paste draft copy and simulate rubric — no live publish."
    if not brand.ready:
        hint = "Fill Brain Pack Brand tab (voice + forbidden claims) before trusting compliance scores."

    return BrandStudioSnapshotOut(
        enabled=True,
        generated_at=now,
        brand_ready=brand.ready,
        brand_char_count=brand.char_count,
        brand_usage_pct=brand.usage_pct,
        sections_filled=sections_filled,
        operator_hint=hint,
        links={
            "brand_pack": brand.href,
            "campaign_launch": "/apps-tools/marketing-team?section=launch#campaign-launch-wizard",
            "publish_queue": "/apps-tools/marketing-team?section=queue#publish-queue",
        },
    )


async def run_brand_studio_rubric_preview(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    body: BrandStudioRubricPreviewIn,
) -> BrandStudioRubricPreviewOut:
    """Score operator copy with marketing-creative + brand-compliance rubrics (simulate-only)."""

    if not settings.brand_studio_rubric_preview_enabled:
        raise ValueError("Brand studio rubric preview is disabled.")

    brand = await compose_brand_context_pack_snapshot(session, tenant_id=tenant_id)
    structured = {
        "title": body.title.strip(),
        "body": body.body.strip(),
        "cta": body.cta.strip(),
        "hashtags": [str(tag).lstrip("#") for tag in body.hashtags[:20]],
    }
    rubric = await evaluate_publish_pack_creative_rubric(
        session,
        structured=structured,
        include_brand_compliance=True,
    )

    hint = rubric.operator_hint or "Simulate-only — approve via publish queue when ready."
    if not brand.ready:
        hint = "Brand pack incomplete — compliance score may be unreliable until Brain Pack Brand is filled."

    return BrandStudioRubricPreviewOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        brand_ready=brand.ready,
        rubric=rubric,
        operator_hint=hint,
    )


__all__ = [
    "BrandStudioRubricPreviewIn",
    "BrandStudioRubricPreviewOut",
    "BrandStudioSnapshotOut",
    "compose_brand_studio_snapshot",
    "run_brand_studio_rubric_preview",
]
