"""Publish Pack — Phase A simulate-only artifacts with validation and archive."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.publish_media import classify_publish_media_url, validate_publish_media_url
from app.core.jwt_tokens import parse_dashboard_user_subject
from app.domain.outputs.engine import OutputEngine
from app.domain.outputs.service import slugify_fragment
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable
from app.infrastructure.persistence.models.tenant import DashboardUserTenantMembership

logger = structlog.get_logger(__name__)

PUBLISH_PACK_FORMAT = "queenswarm.publish_pack.v1"
TAG_PUBLISH_PACK = "publish_pack"
TAG_PUBLISH_PACK_VERIFIED = "publish-pack-verified"
TAG_SIMULATE_ONLY = "simulate_only"
TAG_READY_TO_PUBLISH = "ready_to_publish"

PublishChannel = Literal["instagram", "facebook", "twitter", "tiktok", "linkedin", "newsletter", "blog", "multi", "other"]

_RE_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", re.IGNORECASE)
_RE_SECRET = re.compile(
    r"(sk-[a-zA-Z0-9]{20,}|BEARER\s+[A-Za-z0-9._-]{20,}|API[_-]?KEY[=:]\s*[A-Za-z0-9_-]{20,})",
    re.IGNORECASE,
)


class PublishPackSnippet(BaseModel):
    """One social snippet inside a publish pack."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=280)
    cta: str = Field(default="", max_length=120)
    hashtags: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("hashtags")
    @classmethod
    def _normalize_hashtags(cls, value: list[str]) -> list[str]:
        out: list[str] = []
        for raw in value[:12]:
            tag = str(raw).strip().lstrip("#")[:48]
            if tag:
                out.append(tag)
        return out


class PublishPackArtifact(BaseModel):
    """Validated publish pack — simulate-only in Phase A."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    format: str = Field(default=PUBLISH_PACK_FORMAT)
    artifact_type: Literal["publish_pack"] = "publish_pack"
    channel: PublishChannel = "instagram"
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=8000)
    hashtags: list[str] = Field(default_factory=list, max_length=20)
    cta: str = Field(default="", max_length=200)
    media_url: str | None = Field(default=None, max_length=500)
    video_url: str | None = Field(default=None, max_length=500)
    scheduled_at: str | None = Field(default=None, max_length=64)
    simulate_only: bool = True
    social_account_id: str | None = Field(default=None, max_length=64)
    snippets: list[PublishPackSnippet] = Field(default_factory=list, max_length=8)

    @field_validator("channel", mode="before")
    @classmethod
    def _normalize_channel(cls, value: Any) -> str:
        return str(value or "instagram").strip().lower()

    @field_validator("simulate_only")
    @classmethod
    def _enforce_simulate_only(cls, value: bool) -> bool:
        if not value:
            msg = "Phase A publish packs must have simulate_only=true."
            raise ValueError(msg)
        return True

    @field_validator("media_url")
    @classmethod
    def _normalize_media_url(cls, value: str | None) -> str | None:
        text = str(value or "").strip()
        return text or None

    @field_validator("video_url")
    @classmethod
    def _normalize_video_url(cls, value: str | None) -> str | None:
        text = str(value or "").strip()
        return text or None

    @model_validator(mode="after")
    def _merge_video_url_for_tiktok(self) -> PublishPackArtifact:
        if self.channel == "tiktok" and self.video_url and not self.media_url:
            return self.model_copy(update={"media_url": self.video_url})
        return self

    @model_validator(mode="after")
    def _validate_media_url_for_channel(self) -> PublishPackArtifact:
        ok, message, _ = validate_publish_media_url(
            self.media_url,
            channel=self.channel,
            required=False,
        )
        if not ok:
            raise ValueError(message)
        return self

    @field_validator("hashtags")
    @classmethod
    def _normalize_hashtags(cls, value: list[str]) -> list[str]:
        out: list[str] = []
        for raw in value[:20]:
            tag = str(raw).strip().lstrip("#")[:48]
            if tag:
                out.append(tag)
        return out


class PublishPackValidationError(ValueError):
    """Raised when publish pack fails schema or security checks."""


def _looks_like_secret(text: str) -> bool:
    return _RE_SECRET.search(text) is not None


def extract_publish_pack_json(text: str) -> dict[str, Any] | None:
    """Parse publish pack JSON from fenced block or inline object."""

    raw = (text or "").strip()
    if not raw:
        return None

    for match in _RE_JSON_BLOCK.finditer(raw):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("artifact_type") == "publish_pack":
            return payload

    start = raw.find('{"artifact_type": "publish_pack"')
    if start < 0:
        start = raw.find('{"artifact_type":"publish_pack"')
    if start >= 0:
        depth = 0
        for idx in range(start, min(len(raw), start + 12000)):
            ch = raw[idx]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        payload = json.loads(raw[start : idx + 1])
                    except json.JSONDecodeError:
                        return None
                    if isinstance(payload, dict):
                        return payload
                    return None
    return None


def validate_publish_pack(payload: dict[str, Any]) -> PublishPackArtifact:
    """Validate publish pack schema and security constraints."""

    if _looks_like_secret(json.dumps(payload)):
        raise PublishPackValidationError("Publish pack contains secret-shaped tokens.")
    try:
        pack = PublishPackArtifact.model_validate(payload)
    except Exception as exc:
        raise PublishPackValidationError(str(exc)) from exc
    combined = f"{pack.title}\n{pack.body}\n{pack.cta}"
    if _looks_like_secret(combined):
        raise PublishPackValidationError("Publish pack body contains secret-shaped tokens.")
    return pack


def build_publish_pack_markdown(pack: PublishPackArtifact, *, critic_excerpt: str = "") -> str:
    """Render human-readable archive body."""

    lines = [
        f"# Publish Pack — {pack.title}",
        "",
        f"- **Channel:** {pack.channel}",
        f"- **Simulate only:** {pack.simulate_only}",
        f"- **Scheduled:** {pack.scheduled_at or 'unscheduled'}",
        "",
        "## Body",
        pack.body,
        "",
    ]
    if pack.hashtags:
        lines.extend(["## Hashtags", " ".join(f"#{t}" for t in pack.hashtags), ""])
    if pack.cta:
        lines.extend(["## CTA", pack.cta, ""])
    if pack.snippets:
        lines.append("## Social snippets")
        for idx, snip in enumerate(pack.snippets, start=1):
            tags = " ".join(f"#{t}" for t in snip.hashtags)
            lines.append(f"{idx}. {snip.text} {tags}".strip())
        lines.append("")
    if critic_excerpt.strip():
        lines.extend(["## Critic verification", critic_excerpt.strip()[:2000], ""])
    return "\n".join(lines).strip()


async def resolve_dashboard_user_for_session(
    db: AsyncSession,
    *,
    supervisor_session: SupervisorSession,
) -> uuid.UUID | None:
    """Resolve archive owner from session subject or tenant owner membership."""

    subject = str(supervisor_session.created_by_subject or "").strip()
    if subject:
        parsed = parse_dashboard_user_subject(subject)
        if parsed is not None:
            return parsed

    tenant_id = supervisor_session.tenant_id
    if tenant_id is None:
        return None

    row = await db.scalar(
        select(DashboardUserTenantMembership)
        .where(
            DashboardUserTenantMembership.tenant_id == tenant_id,
            DashboardUserTenantMembership.role.in_(("owner", "admin")),
        )
        .order_by(DashboardUserTenantMembership.created_at.asc())
        .limit(1),
    )
    return row.dashboard_user_id if row is not None else None


async def archive_verified_publish_pack(
    db: AsyncSession,
    *,
    supervisor_session: SupervisorSession,
    pack: PublishPackArtifact,
    critic_excerpt: str = "",
    verified: bool = True,
) -> TaskFinalDeliverable | None:
    """Persist publish pack to Outputs archive (simulate-only)."""

    dashboard_user_id = await resolve_dashboard_user_for_session(db, supervisor_session=supervisor_session)
    tenant = None
    if supervisor_session.tenant_id is not None:
        from app.infrastructure.persistence.models.tenant import Tenant

        tenant = await db.get(Tenant, supervisor_session.tenant_id)

    from app.application.services.publish_pack_media_hook import maybe_enrich_publish_pack_media
    from app.application.services.publish_pack_video_hook import maybe_enrich_tiktok_video_media

    pack = await maybe_enrich_publish_pack_media(
        db,
        pack=pack,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
    )
    pack = await maybe_enrich_tiktok_video_media(
        db,
        pack=pack,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
    )

    from app.application.services.publish_hook_variants import generate_publish_hook_variants
    from app.core.config import settings as app_settings

    hook_variants: list[dict[str, Any]] = []
    if app_settings.publish_hook_variants_enabled:
        hook_variants = generate_publish_hook_variants(
            title=pack.title,
            body=pack.body,
            channel=pack.channel,
        )

    markdown = build_publish_pack_markdown(pack, critic_excerpt=critic_excerpt)
    structured = pack.model_dump()
    structured["supervisor_session_id"] = str(supervisor_session.id)
    structured["verified"] = verified
    if hook_variants:
        structured["hook_variants"] = hook_variants
        structured["best_hook_variant"] = hook_variants[0]
        structured["best_hook_confidence"] = float(hook_variants[0].get("confidence") or 0.0)
    if pack.media_url:
        structured["media_kind"] = classify_publish_media_url(pack.media_url) or "unknown"

    tag_base = [TAG_PUBLISH_PACK, TAG_SIMULATE_ONLY, pack.channel, "marketing"]
    if verified:
        tag_base.extend([TAG_PUBLISH_PACK_VERIFIED, TAG_READY_TO_PUBLISH])
    else:
        tag_base.append("draft")

    tags = sorted(dict.fromkeys(tag_base))

    lineage_id = supervisor_session.id
    row = await OutputEngine.create_final_deliverable(
        db,
        lineage_id=lineage_id,
        markdown_body=markdown,
        structured=structured,
        title_hint=pack.title[:200],
        slug_hint=slugify_fragment(pack.title[:120]),
        tags=tags,
        voice_script=None,
        dashboard_user_id=dashboard_user_id,
        ballroom_session_id=None,
        mission_id=supervisor_session.task_id,
        source_task_id=supervisor_session.task_id,
    )

    summary = dict(supervisor_session.context_summary or {})
    summary["publish_pack_archived"] = True
    summary["publish_pack_deliverable_id"] = str(row.id)
    supervisor_session.context_summary = summary
    await db.flush()

    logger.info(
        "publish_pack.archived",
        agent_id="publish_pack",
        swarm_id=str(supervisor_session.id),
        task_id=str(row.id),
        channel=pack.channel,
    )

    if verified and dashboard_user_id is not None:
        from app.application.services.trust_autopilot_notify import notify_publish_pack_simulate_ready

        await notify_publish_pack_simulate_ready(
            db,
            row=row,
            dashboard_user_id=dashboard_user_id,
        )

    return row


async def try_archive_publish_pack_from_session_output(
    db: AsyncSession,
    *,
    supervisor_session: SupervisorSession,
    combined_output: str,
    critic_excerpt: str = "",
    verified: bool = True,
) -> TaskFinalDeliverable | None:
    """Parse, validate, and archive publish pack when present in LLM output."""

    payload = extract_publish_pack_json(combined_output)
    if payload is None:
        return None

    try:
        pack = validate_publish_pack(payload)
    except PublishPackValidationError as exc:
        logger.warning(
            "publish_pack.validation_failed",
            agent_id="publish_pack",
            swarm_id=str(supervisor_session.id),
            error=str(exc),
        )
        summary = dict(supervisor_session.context_summary or {})
        summary["publish_pack_validation_error"] = str(exc)[:400]
        supervisor_session.context_summary = summary
        await db.flush()
        return None

    existing_id = (supervisor_session.context_summary or {}).get("publish_pack_deliverable_id")
    if existing_id:
        existing = await db.get(TaskFinalDeliverable, uuid.UUID(str(existing_id)))
        if existing is not None:
            return existing

    return await archive_verified_publish_pack(
        db,
        supervisor_session=supervisor_session,
        pack=pack,
        critic_excerpt=critic_excerpt,
        verified=verified,
    )


__all__ = [
    "PUBLISH_PACK_FORMAT",
    "TAG_PUBLISH_PACK",
    "TAG_PUBLISH_PACK_VERIFIED",
    "TAG_READY_TO_PUBLISH",
    "PublishPackArtifact",
    "PublishPackValidationError",
    "archive_verified_publish_pack",
    "build_publish_pack_markdown",
    "extract_publish_pack_json",
    "try_archive_publish_pack_from_session_output",
    "validate_publish_pack",
]
