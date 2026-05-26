"""Social publish — Phase C multi-channel adapter (Instagram, Facebook, X, TikTok)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.execution_studio import execute_studio_tool
from app.application.services.publish_pack import TAG_PUBLISH_PACK_VERIFIED, TAG_SIMULATE_ONLY
from app.application.services.publish_queue import classify_publish_queue_status
from app.application.services.publish_audit import (
    PublishAuditSnapshotOut,
    build_publish_audit_snapshot,
    record_publish_audit_event,
)
from app.application.services.social_connected_accounts import (
    SocialConnectedAccountsSnapshotOut,
    build_social_accounts_snapshot,
    load_account_secrets,
    publish_context_from_account,
    resolve_social_account_for_publish,
)
from app.application.services.tiktok_social_context import TikTokAccountSnapshotOut, build_tiktok_account_snapshot
from app.application.services.meta_social_context import MetaAccountsSnapshotOut, build_meta_accounts_snapshot
from app.application.services.x_social_context import XAccountSnapshotOut, build_x_account_snapshot
from app.core.config import settings
from app.domain.outputs.service import fetch_owned_deliverable
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService
from app.infrastructure.connectors.phase3.catalog import get_phase3_template
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable
from app.infrastructure.persistence.models.tenant import Tenant

logger = structlog.get_logger(__name__)

SocialChannelId = Literal["instagram", "facebook", "twitter", "tiktok", "newsletter"]
SocialPublishMode = Literal["simulate", "live"]

# Channels that require Marketplace OAuth before live social API (excludes newsletter/blog).
SOCIAL_OAUTH_CHANNEL_IDS: frozenset[SocialChannelId] = frozenset(
    {"instagram", "facebook", "twitter", "tiktok"},
)

TAG_SOCIAL_PUBLISH_SIMULATED = "social-publish-simulated"
TAG_SOCIAL_PUBLISH_LIVE = "social-publish-live"

_CHANNEL_REGISTRY: dict[SocialChannelId, dict[str, str]] = {
    "instagram": {
        "label": "Instagram",
        "connector_slug": "instagram_graph",
        "template_id": "instagram_graph_api",
        "publish_tool": "media_create",
        "follow_up_tool": "media_publish",
    },
    "facebook": {
        "label": "Facebook",
        "connector_slug": "facebook_graph",
        "template_id": "facebook_graph_api",
        "publish_tool": "page_photo_publish",
        "follow_up_tool": "page_feed_publish",
    },
    "twitter": {
        "label": "X (Twitter)",
        "connector_slug": "twitter_api_v2",
        "template_id": "twitter_api_v2",
        "publish_tool": "tweets_create",
        "follow_up_tool": "",
    },
    "tiktok": {
        "label": "TikTok",
        "connector_slug": "tiktok_content",
        "template_id": "tiktok_content_posting",
        "publish_tool": "video_publish_init",
        "follow_up_tool": "publish_status_fetch",
    },
    "newsletter": {
        "label": "Newsletter",
        "connector_slug": "gmail_workspace",
        "template_id": "gmail_google_workspace",
        "publish_tool": "drafts_send",
        "follow_up_tool": "",
    },
}


class SocialChannelStatusOut(BaseModel):
    """One social channel connector readiness row."""

    model_config = ConfigDict(extra="ignore")

    channel: SocialChannelId
    label: str
    connector_slug: str
    template_id: str
    installed: bool = False
    active: bool = False
    credentials_ok: bool = False
    publish_tool: str
    live_allowed: bool = False


class SocialPublishReadyItemOut(BaseModel):
    """Approved publish pack eligible for social publish."""

    model_config = ConfigDict(extra="ignore")

    deliverable_id: uuid.UUID
    title: str
    channel: str
    body_preview: str
    media_url: str | None = None
    media_kind: str | None = None
    social_account_id: str | None = None
    tags: list[str] = Field(default_factory=list)


class SocialPublishSnapshotOut(BaseModel):
    """Single snapshot for Social Publish panel."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    live_enabled: bool = False
    generated_at: datetime
    channels: list[SocialChannelStatusOut] = Field(default_factory=list)
    ready_items: list[SocialPublishReadyItemOut] = Field(default_factory=list)
    audit: PublishAuditSnapshotOut | None = None
    meta_accounts: MetaAccountsSnapshotOut | None = None
    x_account: XAccountSnapshotOut | None = None
    tiktok_account: TikTokAccountSnapshotOut | None = None
    connected_accounts: SocialConnectedAccountsSnapshotOut | None = None
    trusted_auto: Any | None = None
    rate_limit: Any | None = None
    links: dict[str, str] = Field(default_factory=dict)


class SocialPublishResultOut(BaseModel):
    """Result of simulate or live social publish."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    mode: SocialPublishMode
    channel: SocialChannelId
    deliverable_id: uuid.UUID
    connector_slug: str
    tool_name: str
    social_account_id: uuid.UUID | None = None
    preview: dict[str, Any] = Field(default_factory=dict)
    upstream: dict[str, Any] | None = None
    message: str = ""
    tags_applied: list[str] = Field(default_factory=list)
    tiktok_status: dict[str, Any] | None = None


class SocialPublishRequestBody(BaseModel):
    """Optional channel override when pack channel is generic."""

    model_config = ConfigDict(extra="forbid")

    channel: SocialChannelId | None = None
    social_account_id: uuid.UUID | None = None
    ig_user_id: str = Field(default="", max_length=64)
    page_id: str = Field(default="", max_length=64)
    operator_confirmed: bool = False


def normalize_social_channel(raw: str) -> SocialChannelId | None:
    """Map publish pack channel string to supported social channel."""

    lowered = raw.strip().lower()
    aliases: dict[str, SocialChannelId] = {
        "instagram": "instagram",
        "ig": "instagram",
        "facebook": "facebook",
        "fb": "facebook",
        "twitter": "twitter",
        "x": "twitter",
        "x-twitter": "twitter",
        "tiktok": "tiktok",
        "tik-tok": "tiktok",
        "newsletter": "newsletter",
        "email": "newsletter",
        "gmail": "newsletter",
    }
    return aliases.get(lowered)


def compose_social_caption(*, body: str, hashtags: list[str], cta: str, max_len: int = 2200) -> str:
    """Build caption/text from publish pack fields."""

    parts: list[str] = [body.strip()]
    if cta.strip():
        parts.append(cta.strip())
    if hashtags:
        tag_line = " ".join(f"#{tag.lstrip('#')}" for tag in hashtags[:20])
        parts.append(tag_line)
    caption = "\n\n".join(p for p in parts if p)
    return caption[:max_len]


def build_social_publish_arguments(
    *,
    channel: SocialChannelId,
    structured: dict[str, Any],
    context: dict[str, str],
    publish_tool: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Return primary tool name + JSON body for connector invoke."""

    caption = compose_social_caption(
        body=str(structured.get("body") or ""),
        hashtags=[str(t) for t in structured.get("hashtags") or []],
        cta=str(structured.get("cta") or ""),
        max_len=280 if channel == "twitter" else 2200,
    )
    media_url = str(structured.get("media_url") or "").strip() or None
    meta = _CHANNEL_REGISTRY[channel]
    tool_name = publish_tool or meta["publish_tool"]

    if channel == "instagram":
        ig_user_id = context.get("ig_user_id") or "{ig_user_id}"
        args: dict[str, Any] = {
            "ig_user_id": ig_user_id,
            "caption": caption,
        }
        if media_url:
            args["image_url"] = media_url
        return tool_name, args

    if channel == "facebook":
        page_id = context.get("page_id") or "{page_id}"
        if media_url:
            return "page_photo_publish", {"page_id": page_id, "url": media_url, "caption": caption}
        return "page_feed_publish", {"page_id": page_id, "message": caption}

    if channel == "twitter":
        return "tweets_create", {"text": caption}

    # tiktok
    if channel == "tiktok":
        return "video_publish_init", {
            "post_info": {
                "title": str(structured.get("title") or caption[:150]),
                "description": caption,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": media_url or "",
            },
        }

    if channel == "newsletter":
        if tool_name == "emails_send":
            html_body = caption.replace("\n", "<br/>")
            return "emails_send", {
                "from": context.get("resend_from") or "",
                "to": context.get("newsletter_to") or "",
                "subject": str(structured.get("title") or "Newsletter"),
                "html": html_body,
            }
        return "drafts_send", {
            "user_id": context.get("gmail_user_id") or "me",
            "subject": str(structured.get("title") or "Newsletter"),
            "body_text": caption,
            "to": context.get("newsletter_to") or "",
        }

    msg = f"Unsupported social channel: {channel}"
    raise ValueError(msg)


_NEWSLETTER_CONNECTOR_CANDIDATES: tuple[tuple[str, str, str], ...] = (
    ("gmail_workspace", "drafts_send", "gmail_google_workspace"),
    ("resend_email", "emails_send", "resend_email_api"),
)


async def resolve_publish_connector(
    session: AsyncSession,
    *,
    channel: SocialChannelId,
) -> tuple[str, str, str]:
    """Resolve connector slug + tool; newsletter prefers first active Gmail or Resend."""

    meta = _CHANNEL_REGISTRY[channel]
    if channel != "newsletter":
        return meta["connector_slug"], meta["publish_tool"], meta["template_id"]

    svc = DynamicConnectorService()
    for slug, tool, template_id in _NEWSLETTER_CONNECTOR_CANDIDATES:
        row = await svc.fetch_by_slug(session, slug=slug)
        if row is None or not row.is_active:
            continue
        secrets = svc._secrets_dict(row)  # noqa: SLF001
        if _connector_credentials_ok(str(row.auth_type or ""), secrets):
            return slug, tool, template_id
    return meta["connector_slug"], meta["publish_tool"], meta["template_id"]


def _connector_credentials_ok(auth_type: str, secrets: dict[str, Any]) -> bool:
    if auth_type == "none":
        return True
    if auth_type in {"api_key", "bearer_token"}:
        return bool(str(secrets.get("api_key") or secrets.get("bearer_token") or "").strip())
    if auth_type == "oauth2":
        return bool(str(secrets.get("oauth2_access_token") or secrets.get("access_token") or "").strip())
    return False


async def _channel_status(
    session: AsyncSession,
    *,
    channel: SocialChannelId,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None = None,
) -> SocialChannelStatusOut:
    meta = _CHANNEL_REGISTRY[channel]
    svc = DynamicConnectorService()
    slug = meta["connector_slug"]
    row = await svc.fetch_by_slug(session, slug=slug)
    installed = row is not None
    active = bool(row.is_active) if row is not None else False
    credentials_ok = False
    if row is not None:
        secrets = svc._secrets_dict(row)  # noqa: SLF001
        credentials_ok = _connector_credentials_ok(str(row.auth_type or ""), secrets)

    if channel in SOCIAL_OAUTH_CHANNEL_IDS and tenant is not None:
        from app.application.services.social_connected_accounts import list_social_accounts

        account_rows = await list_social_accounts(
            session,
            tenant_id=tenant.id,
            channel=channel,  # type: ignore[arg-type]
        )
        if account_rows:
            credentials_ok = True
            active = True
            installed = True

    try:
        get_phase3_template(meta["template_id"])
    except KeyError:
        pass

    return SocialChannelStatusOut(
        channel=channel,
        label=meta["label"],
        connector_slug=slug,
        template_id=meta["template_id"],
        installed=installed,
        active=active and credentials_ok,
        credentials_ok=credentials_ok,
        publish_tool=meta["publish_tool"],
        live_allowed=bool(settings.social_publish_live_enabled),
    )


async def build_social_publish_snapshot(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None = None,
    limit: int = 20,
) -> SocialPublishSnapshotOut:
    """Load channel readiness + approved publish packs in one pass."""

    channels = [
        await _channel_status(session, channel=channel_id, dashboard_user_id=dashboard_user_id, tenant=tenant)
        for channel_id in _CHANNEL_REGISTRY
    ]

    from app.domain.outputs.service import list_owned_deliverables

    rows = await list_owned_deliverables(
        session,
        dashboard_user_id=dashboard_user_id,
        limit=max(limit, 40),
        ready_to_publish=True,
    )
    ready_items: list[SocialPublishReadyItemOut] = []
    for row in rows:
        status = classify_publish_queue_status(row)
        if status != "approved":
            continue
        structured = dict(row.structured_json or {})
        channel_raw = str(structured.get("channel") or "instagram")
        ready_items.append(
            SocialPublishReadyItemOut(
                deliverable_id=row.id,
                title=str(row.title or "Publish pack"),
                channel=channel_raw,
                body_preview=str(structured.get("body") or row.markdown_body or "")[:240],
                media_url=str(structured.get("media_url") or "").strip() or None,
                media_kind=str(structured.get("media_kind") or "").strip() or None,
                social_account_id=str(structured.get("social_account_id") or "").strip() or None,
                tags=list(row.tags or []),
            ),
        )
        if len(ready_items) >= limit:
            break

    meta_accounts = await build_meta_accounts_snapshot(
        session,
        dashboard_user_id=dashboard_user_id,
        oauth_meta_configured=bool(
            settings.oauth_meta_client_id.strip() and settings.oauth_meta_client_secret.strip()
        ),
    )
    x_account = await build_x_account_snapshot(
        session,
        dashboard_user_id=dashboard_user_id,
        oauth_x_configured=bool(settings.oauth_x_client_id.strip() and settings.oauth_x_client_secret.strip()),
    )
    tiktok_account = await build_tiktok_account_snapshot(
        session,
        dashboard_user_id=dashboard_user_id,
        oauth_tiktok_configured=bool(
            settings.oauth_tiktok_client_key.strip() and settings.oauth_tiktok_client_secret.strip()
        ),
    )

    from app.application.services.social_publish_rate_limit import build_social_publish_rate_limit_snapshot
    from app.application.services.social_publish_trusted_auto import build_trusted_auto_policy

    connected_accounts = await build_social_accounts_snapshot(session, tenant=tenant)

    return SocialPublishSnapshotOut(
        enabled=bool(settings.social_publish_enabled),
        live_enabled=bool(settings.social_publish_live_enabled),
        generated_at=datetime.now(tz=UTC),
        channels=channels,
        ready_items=ready_items,
        audit=build_publish_audit_snapshot(tenant, limit=15),
        meta_accounts=meta_accounts,
        x_account=x_account,
        tiktok_account=tiktok_account,
        connected_accounts=connected_accounts,
        trusted_auto=build_trusted_auto_policy(tenant).model_dump(mode="json"),
        rate_limit=(await build_social_publish_rate_limit_snapshot(dashboard_user_id=dashboard_user_id)).model_dump(
            mode="json",
        ),
        links={
            "marketplace": "/integrations?tab=marketplace",
            "publish_queue": "/integrations?tab=studio#publish-queue",
            "outputs": "/outputs?ready_to_publish=true",
            "connector_hub": "/integrations?tab=hub#oauth-consent",
        },
    )


def _require_publishable_row(row: TaskFinalDeliverable) -> dict[str, Any]:
    status = classify_publish_queue_status(row)
    if status != "approved":
        msg = "Deliverable must be publish-queue-approved before social publish."
        raise ValueError(msg)
    tags = {str(t) for t in row.tags or []}
    if TAG_PUBLISH_PACK_VERIFIED not in tags or TAG_SIMULATE_ONLY not in tags:
        msg = "Deliverable missing verified simulate-only publish pack tags."
        raise ValueError(msg)
    structured = dict(row.structured_json or {})
    if not str(structured.get("body") or "").strip():
        msg = "Publish pack body is empty."
        raise ValueError(msg)
    return structured


async def run_social_publish(
    session: AsyncSession,
    *,
    deliverable_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
    mode: SocialPublishMode,
    channel_override: SocialChannelId | None = None,
    social_account_id: uuid.UUID | None = None,
    context: dict[str, str] | None = None,
    operator_confirmed: bool = False,
    reviewed_by: str = "",
) -> SocialPublishResultOut:
    """Simulate or live publish an approved publish pack to a social channel."""

    if not settings.social_publish_enabled:
        raise ValueError("Social publish disabled.")

    row = await fetch_owned_deliverable(
        session,
        deliverable_id=deliverable_id,
        dashboard_user_id=dashboard_user_id,
    )
    if row is None:
        raise LookupError("Deliverable not found.")

    structured = _require_publishable_row(row)
    channel = channel_override or normalize_social_channel(str(structured.get("channel") or ""))
    if channel is None:
        raise ValueError("Unsupported or missing social channel on publish pack.")

    resolved_account = None
    secrets_override: dict[str, Any] | None = None
    if channel in SOCIAL_OAUTH_CHANNEL_IDS:
        resolved_account = await resolve_social_account_for_publish(
            session,
            tenant=tenant,
            channel=channel,  # type: ignore[arg-type]
            account_id=social_account_id,
            structured=structured,
        )
        if resolved_account is not None:
            secrets_override = load_account_secrets(resolved_account)
        else:
            legacy_slug = _CHANNEL_REGISTRY[channel]["connector_slug"]
            legacy_row = await DynamicConnectorService().fetch_by_slug(session, slug=legacy_slug)
            if legacy_row is not None:
                legacy_secrets = DynamicConnectorService()._secrets_dict(legacy_row)  # noqa: SLF001
                if _connector_credentials_ok(str(legacy_row.auth_type or ""), legacy_secrets):
                    secrets_override = legacy_secrets
            if secrets_override is None:
                raise ValueError(
                    f"No connected {channel} account — connect one in Social publish or specify social_account_id.",
                )

    from app.application.services.meta_social_context import enrich_meta_publish_context

    publish_context = dict(context or {})
    if resolved_account is not None:
        publish_context = {**publish_context_from_account(resolved_account), **publish_context}

    publish_context = await enrich_meta_publish_context(
        session,
        dashboard_user_id=dashboard_user_id,
        channel=channel,
        context=publish_context,
    )

    meta = _CHANNEL_REGISTRY[channel]
    connector_slug = (
        resolved_account.connector_slug
        if resolved_account is not None
        else (await resolve_publish_connector(session, channel=channel))[0]
    )
    _, publish_tool, _template_id = await resolve_publish_connector(session, channel=channel)
    tool_name, arguments = build_social_publish_arguments(
        channel=channel,
        structured=structured,
        context=publish_context,
        publish_tool=publish_tool,
    )

    preview = {
        "channel": channel,
        "connector_slug": connector_slug,
        "tool_name": tool_name,
        "arguments": arguments,
        "title": str(structured.get("title") or row.title or ""),
        "media_url": structured.get("media_url"),
        "caption_preview": arguments.get("caption") or arguments.get("message") or arguments.get("text"),
        "social_account_id": str(resolved_account.id) if resolved_account is not None else None,
        "social_account_label": resolved_account.label if resolved_account is not None else None,
    }

    from app.application.services.publish_media import validate_publish_media_url

    media_ok, media_message, _ = validate_publish_media_url(
        str(structured.get("media_url") or "").strip() or None,
        channel=channel,
        required=channel == "tiktok",
    )
    if not media_ok:
        return SocialPublishResultOut(
            ok=False,
            mode=mode,
            channel=channel,
            deliverable_id=deliverable_id,
            connector_slug=connector_slug,
            tool_name=tool_name,
            preview=preview,
            message=media_message,
        )

    if mode == "live" and not settings.social_publish_live_enabled:
        return SocialPublishResultOut(
            ok=False,
            mode=mode,
            channel=channel,
            deliverable_id=deliverable_id,
            connector_slug=connector_slug,
            tool_name=tool_name,
            preview=preview,
            message="Live social publish disabled — set SOCIAL_PUBLISH_LIVE_ENABLED=true after Meta/X/TikTok OAuth.",
        )

    from app.application.services.social_publish_trusted_auto import resolve_trusted_auto_live_confirmation

    confirm_reason = "manual_confirm" if operator_confirmed else ""
    effective_confirmed = operator_confirmed
    if mode == "live":
        effective_confirmed, confirm_reason = resolve_trusted_auto_live_confirmation(
            tenant=tenant,
            channel=channel,
            operator_confirmed=operator_confirmed,
            row=row,
        )
    if mode == "live" and not effective_confirmed:
        reason_messages = {
            "trusted_auto_global_off": "Live publish requires operator_confirmed=true (trusted auto disabled globally).",
            "live_disabled": "Live social publish disabled.",
            "tenant_missing": "Tenant context required for live publish.",
            "trusted_auto_tenant_off": "Enable trusted auto-publish in Social publish settings or confirm manually.",
            "channel_manual_mode": "Channel is manual mode — click Live with confirmation.",
            "pack_not_simulated": "Run Simulate on this pack before live (or auto-live).",
            "insufficient_channel_simulates": (
                "Channel needs more successful simulates before auto-live — keep using manual Live or lower threshold."
            ),
        }
        from app.application.services.trust_autopilot_notify import notify_live_publish_gate

        await notify_live_publish_gate(
            session,
            row=row,
            dashboard_user_id=dashboard_user_id,
            channel=channel,
            reason=confirm_reason,
        )
        return SocialPublishResultOut(
            ok=False,
            mode=mode,
            channel=channel,
            deliverable_id=deliverable_id,
            connector_slug=connector_slug,
            tool_name=tool_name,
            preview=preview,
            message=reason_messages.get(confirm_reason, "Live publish requires operator_confirmed=true."),
        )

    if mode == "live":
        from app.application.services.social_publish_rate_limit import check_social_publish_rate_limit

        allowed, rate_message = await check_social_publish_rate_limit(
            dashboard_user_id=dashboard_user_id,
            channel=channel,
            mode=mode,
        )
        if not allowed:
            return SocialPublishResultOut(
                ok=False,
                mode=mode,
                channel=channel,
                deliverable_id=deliverable_id,
                connector_slug=connector_slug,
                tool_name=tool_name,
                preview=preview,
                message=rate_message,
            )

    upstream = await execute_studio_tool(
        session,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
        connector_slug=connector_slug,
        tool_name=tool_name,
        arguments=arguments,
        mode=mode,
        operator_confirmed=effective_confirmed if mode == "live" else operator_confirmed,
        secrets_override=secrets_override,
    )

    ok = bool(upstream.get("ok"))
    tags_applied: list[str] = []
    if ok:
        tag = TAG_SOCIAL_PUBLISH_SIMULATED if mode == "simulate" else TAG_SOCIAL_PUBLISH_LIVE
        merged = sorted(dict.fromkeys([*(row.tags or []), tag]))
        row.tags = merged
        tags_applied = [tag]
        await session.flush()
        logger.info(
            "social_publish.completed",
            agent_id="social_publish",
            swarm_id=connector_slug,
            task_id=str(deliverable_id),
            channel=channel,
            mode=mode,
            reviewed_by=reviewed_by[:120],
        )
        if mode == "simulate":
            from app.application.services.trust_autopilot_notify import notify_social_simulate_ready_for_live

            await notify_social_simulate_ready_for_live(
                session,
                row=row,
                dashboard_user_id=dashboard_user_id,
                channel=channel,
            )

    message = str(upstream.get("message") or "")
    if upstream.get("error") == "approval_required":
        message = "Connector requires live approval — confirm in Execution Studio policy."
    elif upstream.get("error") == "connector_not_found":
        message = f"Install {meta['label']} from Tools Marketplace first."

    await record_publish_audit_event(
        session,
        tenant,
        kind=(
            "social_simulate"
            if mode == "simulate"
            else ("social_live_auto" if confirm_reason == "trusted_auto" else "social_live")
        ),
        message=message or f"Social publish {mode}: {'OK' if ok else 'blocked'}",
        deliverable_id=deliverable_id,
        title=str(row.title or ""),
        channel=channel,
        mode=mode,
        ok=ok,
        connector_slug=connector_slug,
        reviewed_by=reviewed_by or ("trusted_auto" if confirm_reason == "trusted_auto" else None),
    )

    if ok and mode == "live" and confirm_reason == "trusted_auto":
        from app.application.services.publish_queue_notify import notify_social_publish_auto_live

        await notify_social_publish_auto_live(
            session,
            row=row,
            dashboard_user_id=dashboard_user_id,
            channel=channel,
        )

    tiktok_status_payload: dict[str, Any] | None = None
    if channel == "tiktok" and ok:
        from app.application.services.tiktok_publish_status import (
            extract_tiktok_publish_id,
            poll_tiktok_publish_status,
        )

        publish_id = extract_tiktok_publish_id(upstream)
        if publish_id:
            status_out = await poll_tiktok_publish_status(
                session,
                dashboard_user_id=dashboard_user_id,
                tenant=tenant,
                publish_id=publish_id,
                mode=mode,
                operator_confirmed=effective_confirmed if mode == "live" else operator_confirmed,
            )
            tiktok_status_payload = status_out.model_dump(mode="json")
            if status_out.status == "failed":
                ok = False
                message = status_out.message or message
            elif status_out.message and not message:
                message = status_out.message

            await record_publish_audit_event(
                session,
                tenant,
                kind="tiktok_publish_status",
                message=status_out.message or f"TikTok publish status: {status_out.status}",
                deliverable_id=deliverable_id,
                title=str(row.title or ""),
                channel=channel,
                mode=mode,
                ok=status_out.status in {"published", "simulated"},
                connector_slug=connector_slug,
                extra_payload={
                    "publish_id": status_out.publish_id,
                    "tiktok_status": status_out.status,
                    "attempts": status_out.attempts,
                    "raw_status": status_out.raw_status,
                },
            )

    return SocialPublishResultOut(
        ok=ok,
        mode=mode,
        channel=channel,
        deliverable_id=deliverable_id,
        connector_slug=connector_slug,
        tool_name=tool_name,
        social_account_id=resolved_account.id if resolved_account is not None else None,
        preview=preview,
        upstream=upstream,
        message=message,
        tags_applied=tags_applied,
        tiktok_status=tiktok_status_payload,
    )


__all__ = [
    "SOCIAL_OAUTH_CHANNEL_IDS",
    "SocialChannelId",
    "SocialPublishRequestBody",
    "SocialPublishResultOut",
    "SocialPublishSnapshotOut",
    "TAG_SOCIAL_PUBLISH_LIVE",
    "TAG_SOCIAL_PUBLISH_SIMULATED",
    "build_social_publish_arguments",
    "build_social_publish_snapshot",
    "compose_social_caption",
    "normalize_social_channel",
    "resolve_publish_connector",
    "run_social_publish",
]
