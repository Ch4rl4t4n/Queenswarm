"""Canonical Phase 3 Communication & Knowledge connector templates.

Templates compile into :class:`~app.connectors.dynamic.schemas.DynamicConnectorCreateBody`
compatible MCP manifests executed by :func:`~app.connectors.dynamic.service.invoke_dynamic_tool`.

Upstream REST quirks (Slack JSON POST bodies, OAuth refresh, multi-part Gmail sends) remain
operator-owned — manifests encode the *happy-path* JSON surfaces Queenswarm can proxy today.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CategoryLiteral = Literal["email", "calendar", "devtools", "chat", "knowledge", "billing", "vault"]
AuthLiteral = Literal["none", "api_key", "bearer_token", "oauth2"]


class Phase3ConnectorTemplate(BaseModel):
    """Dashboard-facing preset describing outbound MCP-shaped HTTP tools."""

    model_config = ConfigDict(frozen=True)

    template_id: str = Field(..., min_length=2, max_length=96)
    category: CategoryLiteral
    title: str = Field(..., min_length=2, max_length=160)
    summary: str = Field(..., min_length=8, max_length=1024)
    documentation_url: str = Field(..., min_length=8, max_length=2048)
    suggested_slug: str = Field(..., min_length=2, max_length=128)
    auth_type: AuthLiteral
    base_url: str | None = Field(default=None, max_length=2048)
    suggested_manager_slugs: tuple[str, ...] = Field(default_factory=tuple)
    tools: tuple[dict[str, Any], ...]


def _hdr(version: str) -> dict[str, str]:
    """Emit Notion-style optional manifest headers."""

    return {"Notion-Version": version}


_PHASE3_RAW: tuple[Phase3ConnectorTemplate, ...] = (
    Phase3ConnectorTemplate(
        template_id="gmail_google_workspace",
        category="email",
        title="Gmail · Google Workspace",
        summary=(
            "List/read/send Gmail threads via Gmail API v1. OAuth2 bearer recommended; "
            "auto-reply & summaries are composed by swarm workers using read + send tools."
        ),
        documentation_url="https://developers.google.com/gmail/api/reference/rest",
        suggested_slug="gmail_workspace",
        auth_type="oauth2",
        base_url="https://gmail.googleapis.com",
        suggested_manager_slugs=("execution_operations", "personal_life", "content_creation"),
        tools=(
            {
                "name": "messages_list",
                "path": "/gmail/v1/users/{user_id}/messages",
                "method": "GET",
                "description": "Paginate mailbox headers (maps unused args to query params).",
            },
            {
                "name": "messages_get",
                "path": "/gmail/v1/users/{user_id}/messages/{id}",
                "method": "GET",
                "description": "Fetch full message JSON including payload references.",
            },
            {
                "name": "messages_send",
                "path": "/gmail/v1/users/{user_id}/messages/send",
                "method": "POST",
                "description": "Send RFC822 base64url payload via JSON `{raw}` produced upstream.",
            },
            {
                "name": "attachments_get",
                "path": "/gmail/v1/users/{user_id}/messages/{message_id}/attachments/{attachment_id}",
                "method": "GET",
                "description": "Download attachment body metadata.",
            },
            {
                "name": "threads_get",
                "path": "/gmail/v1/users/{user_id}/threads/{id}",
                "method": "GET",
                "description": "Fetch collapsed thread for Ballroom summarisation prompts.",
            },
            {
                "name": "drafts_create",
                "path": "/gmail/v1/users/{user_id}/drafts",
                "method": "POST",
                "description": "Stage composer drafts — pair with verified swarm copy before send.",
            },
            {
                "name": "drafts_send",
                "path": "/gmail/v1/users/{user_id}/drafts/send",
                "method": "POST",
                "description": "Transmit RFC822 drafts `{id}` once simulations approve auto-replies.",
            },
            {
                "name": "users_labels_list",
                "path": "/gmail/v1/users/{user_id}/labels",
                "method": "GET",
                "description": "Discover mailbox labels for routing + filtering helpers.",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="outlook_microsoft365",
        category="email",
        title="Outlook · Microsoft Graph",
        summary="Enterprise mailbox access + Microsoft Graph sendMail surfaces.",
        documentation_url="https://learn.microsoft.com/graph/api/resources/mail-api-overview",
        suggested_slug="outlook_graph",
        auth_type="oauth2",
        base_url="https://graph.microsoft.com/v1.0",
        suggested_manager_slugs=("execution_operations", "personal_life", "review_quality"),
        tools=(
            {
                "name": "messages_list",
                "path": "/users/{user_id}/messages",
                "method": "GET",
                "description": "List messages for `user_id` (typically `me`).",
            },
            {
                "name": "messages_get",
                "path": "/users/{user_id}/messages/{message_id}",
                "method": "GET",
                "description": "Hydrate message including attachments collection.",
            },
            {
                "name": "send_mail",
                "path": "/users/{user_id}/sendMail",
                "method": "POST",
                "description": "POST Graph sendMail envelope `{message:{subject,body,toRecipients}}`.",
            },
            {
                "name": "attachments_download_meta",
                "path": "/users/{user_id}/messages/{message_id}/attachments/{attachment_id}",
                "method": "GET",
                "description": "Resolve attachment bytes references.",
            },
            {
                "name": "message_create_reply_draft",
                "path": "/users/{user_id}/messages/{message_id}/createReply",
                "method": "POST",
                "description": "Bootstrap draft replies — hydrate JSON body before Microsoft Graph send.",
            },
            {
                "name": "message_reply_send",
                "path": "/users/{user_id}/messages/{message_id}/reply",
                "method": "POST",
                "description": "POST `{comment}` payloads for verified auto-replies after Ballroom review.",
            },
            {
                "name": "mail_folders_list",
                "path": "/users/{user_id}/mailFolders",
                "method": "GET",
                "description": "Enumerate WellKnown folders for routing automation.",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="google_calendar",
        category="calendar",
        title="Google Calendar",
        summary=(
            "Read/write Calendar events, enable auto-book flows; pair Ballroom summaries via hive memo endpoint."
        ),
        documentation_url="https://developers.google.com/calendar/api/guides/overview",
        suggested_slug="google_calendar",
        auth_type="oauth2",
        base_url="https://www.googleapis.com/calendar/v3",
        suggested_manager_slugs=("execution_operations", "personal_life", "optimization"),
        tools=(
            {
                "name": "events_list",
                "path": "/calendars/{calendar_id}/events",
                "method": "GET",
                "description": "List events with optional `timeMin`, `timeMax`, `singleEvents` query args.",
            },
            {
                "name": "events_insert",
                "path": "/calendars/{calendar_id}/events",
                "method": "POST",
                "description": "Create confirmed events from Ballroom-approved drafts.",
            },
            {
                "name": "events_patch",
                "path": "/calendars/{calendar_id}/events/{event_id}",
                "method": "PATCH",
                "description": "Apply reschedule / conferencing metadata updates.",
            },
            {
                "name": "events_delete",
                "path": "/calendars/{calendar_id}/events/{event_id}",
                "method": "DELETE",
                "description": "Cancel meetings when simulations fail verification.",
            },
            {
                "name": "freebusy_query",
                "path": "/freeBusy",
                "method": "POST",
                "description": "Collision detection `{timeMin,timeMax,items:[{id}]}` before Ballroom auto-book.",
            },
            {
                "name": "calendars_list",
                "path": "/users/me/calendarList",
                "method": "GET",
                "description": "Discover writable calendars for delegated booking lanes.",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="github_rest",
        category="devtools",
        title="GitHub REST",
        summary="Issues, pull requests, reviews, merges via GitHub REST v3.",
        documentation_url="https://docs.github.com/en/rest",
        suggested_slug="github_rest",
        auth_type="bearer_token",
        base_url="https://api.github.com",
        suggested_manager_slugs=("review_quality", "execution_operations", "research_intelligence"),
        tools=(
            {
                "name": "issues_list",
                "path": "/repos/{owner}/{repo}/issues",
                "method": "GET",
                "description": "Enumerate issues with filters passed as unused query args.",
            },
            {
                "name": "issues_create",
                "path": "/repos/{owner}/{repo}/issues",
                "method": "POST",
                "description": "Open tracking issues from swarm escalations.",
            },
            {
                "name": "pulls_list",
                "path": "/repos/{owner}/{repo}/pulls",
                "method": "GET",
                "description": "List PRs awaiting Ballroom review hints.",
            },
            {
                "name": "pulls_merge",
                "path": "/repos/{owner}/{repo}/pulls/{pull_number}/merge",
                "method": "PUT",
                "description": "Merge verified PRs after Review manager simulation passes.",
            },
            {
                "name": "pulls_create_review",
                "path": "/repos/{owner}/{repo}/pulls/{pull_number}/reviews",
                "method": "POST",
                "description": "Publish structured review comments.",
            },
            {
                "name": "pulls_get",
                "path": "/repos/{owner}/{repo}/pulls/{pull_number}",
                "method": "GET",
                "description": "Hydrate PR metadata before merge simulation.",
            },
            {
                "name": "repos_get",
                "path": "/repos/{owner}/{repo}",
                "method": "GET",
                "description": "Resolve default branch + permissions for Ballroom code-review flows.",
            },
            {
                "name": "repos_contents_get",
                "path": "/repos/{owner}/{repo}/contents/{path}",
                "method": "GET",
                "description": "Fetch files via `{path}` plus unused `ref` query args.",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="gitlab_rest",
        category="devtools",
        title="GitLab REST",
        summary="Issues + merge requests on GitLab.com or self-managed `/api/v4` roots.",
        documentation_url="https://docs.gitlab.com/ee/api/",
        suggested_slug="gitlab_rest",
        auth_type="bearer_token",
        base_url="https://gitlab.com/api/v4",
        suggested_manager_slugs=("review_quality", "execution_operations", "research_intelligence"),
        tools=(
            {
                "name": "projects_search",
                "path": "/projects",
                "method": "GET",
                "description": "Discover projects (pass `search`, `membership`, etc. as query args).",
            },
            {
                "name": "issues_list",
                "path": "/projects/{project_id}/issues",
                "method": "GET",
                "description": "List issues for numeric/string project id.",
            },
            {
                "name": "merge_requests_list",
                "path": "/projects/{project_id}/merge_requests",
                "method": "GET",
                "description": "Track MR queue states.",
            },
            {
                "name": "merge_request_merge",
                "path": "/projects/{project_id}/merge_requests/{merge_request_iid}/merge",
                "method": "PUT",
                "description": "Merge when consensus + simulations succeed.",
            },
            {
                "name": "merge_requests_get",
                "path": "/projects/{project_id}/merge_requests/{merge_request_iid}",
                "method": "GET",
                "description": "Inspect MR diffs + approvals before Ballroom merge.",
            },
            {
                "name": "projects_get",
                "path": "/projects/{project_id}",
                "method": "GET",
                "description": "Resolve visibility + shared runners configuration.",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="slack_web_api",
        category="chat",
        title="Slack Web API",
        summary="Channels, threads, reactions, notifications via HTTPS JSON + bearer tokens.",
        documentation_url="https://api.slack.com/web",
        suggested_slug="slack_workspace",
        auth_type="bearer_token",
        base_url="https://slack.com/api",
        suggested_manager_slugs=("execution_operations", "content_creation", "optimization"),
        tools=(
            {
                "name": "chat_post_message",
                "path": "/chat.postMessage",
                "method": "POST",
                "description": "Post threaded updates — supply `channel`, `thread_ts`, `text`.",
            },
            {
                "name": "conversations_history",
                "path": "/conversations.history",
                "method": "POST",
                "description": "Retrieve channel transcripts for hive summaries.",
            },
            {
                "name": "reactions_add",
                "path": "/reactions.add",
                "method": "POST",
                "description": "Ack swarm milestones with emoji reactions.",
            },
            {
                "name": "conversations_open",
                "path": "/conversations.open",
                "method": "POST",
                "description": "Open DM/channel contexts before threaded notifications.",
            },
            {
                "name": "conversations_replies",
                "path": "/conversations.replies",
                "method": "POST",
                "description": "Hydrate thread tails for hive summaries.",
            },
            {
                "name": "chat_schedule_message",
                "path": "/chat.scheduleMessage",
                "method": "POST",
                "description": "Defer outbound announcements until verification completes.",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="telegram_bot_api",
        category="chat",
        title="Telegram Bot API",
        summary=(
            "Bot outbound messaging — set base URL to `https://api.telegram.org/bot<token>/` "
            "(token stays outside ciphertext while Queenswarm stages HTTPS proxy)."
        ),
        documentation_url="https://core.telegram.org/bots/api",
        suggested_slug="telegram_bot",
        auth_type="none",
        base_url=None,
        suggested_manager_slugs=("execution_operations", "personal_life"),
        tools=(
            {
                "name": "send_message",
                "path": "/sendMessage",
                "method": "POST",
                "description": "Chat messages — JSON `{chat_id,text}`.",
            },
            {
                "name": "get_updates",
                "path": "/getUpdates",
                "method": "POST",
                "description": "Long-poll stub — prefer webhooks in prod.",
            },
            {
                "name": "answer_inline_query",
                "path": "/answerInlineQuery",
                "method": "POST",
                "description": "Respond to inline queries for lightweight operator lookups.",
            },
            {
                "name": "set_webhook",
                "path": "/setWebhook",
                "method": "POST",
                "description": "Register HTTPS webhook endpoints for durable notifications.",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="discord_bot_api",
        category="chat",
        title="Discord Bot API",
        summary="Channel messaging + lightweight moderation hooks via API v10.",
        documentation_url="https://discord.com/developers/docs/reference",
        suggested_slug="discord_guild",
        auth_type="bearer_token",
        base_url="https://discord.com/api/v10",
        suggested_manager_slugs=("execution_operations", "content_creation"),
        tools=(
            {
                "name": "channel_messages_list",
                "path": "/channels/{channel_id}/messages",
                "method": "GET",
                "description": "Pull recent messages before summarisation.",
            },
            {
                "name": "channel_message_create",
                "path": "/channels/{channel_id}/messages",
                "method": "POST",
                "description": "Notify hive operators with structured embed JSON.",
            },
            {
                "name": "channel_message_add_reaction",
                "path": "/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me",
                "method": "PUT",
                "description": "Lightweight acknowledgement reactions.",
            },
            {
                "name": "guild_channels_list",
                "path": "/guilds/{guild_id}/channels",
                "method": "GET",
                "description": "Discover channel IDs for routing Ballroom alerts.",
            },
            {
                "name": "channel_messages_crosspost",
                "path": "/channels/{channel_id}/messages/{message_id}/crosspost",
                "method": "POST",
                "description": "Fan-out announcements after verification.",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="notion_workspace",
        category="knowledge",
        title="Notion API",
        summary="CRUD pages + databases with enforced Notion-Version headers on tools.",
        documentation_url="https://developers.notion.com/reference",
        suggested_slug="notion_workspace",
        auth_type="bearer_token",
        base_url="https://api.notion.com/v1",
        suggested_manager_slugs=("research_intelligence", "content_creation", "optimization"),
        tools=(
            {
                "name": "retrieve_page",
                "path": "/pages/{page_id}",
                "method": "GET",
                "headers": _hdr("2022-06-28"),
                "description": "Hydrate page metadata + properties.",
            },
            {
                "name": "update_page",
                "path": "/pages/{page_id}",
                "method": "PATCH",
                "headers": _hdr("2022-06-28"),
                "description": "Apply verified knowledge mutations.",
            },
            {
                "name": "database_query",
                "path": "/databases/{database_id}/query",
                "method": "POST",
                "headers": _hdr("2022-06-28"),
                "description": "Filtered database sync for Recipe/Knowledge bridges.",
            },
            {
                "name": "create_page",
                "path": "/pages",
                "method": "POST",
                "headers": _hdr("2022-06-28"),
                "description": "Author new knowledge rows parented to databases.",
            },
            {
                "name": "search",
                "path": "/search",
                "method": "POST",
                "headers": _hdr("2022-06-28"),
                "description": "Workspace semantic sweep `{query,filter}` before CRUD.",
            },
            {
                "name": "databases_retrieve",
                "path": "/databases/{database_id}",
                "method": "GET",
                "headers": _hdr("2022-06-28"),
                "description": "Inspect schema prior to database sync jobs.",
            },
            {
                "name": "blocks_children_append",
                "path": "/blocks/{block_id}/children",
                "method": "PATCH",
                "headers": _hdr("2022-06-28"),
                "description": "Append verified knowledge sections post-simulation.",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="stripe_billing",
        category="billing",
        title="Stripe API",
        summary="Invoices, payments, subscriptions with idempotent REST proxies.",
        documentation_url="https://stripe.com/docs/api",
        suggested_slug="stripe_billing",
        auth_type="bearer_token",
        base_url="https://api.stripe.com/v1",
        suggested_manager_slugs=("execution_operations", "optimization"),
        tools=(
            {
                "name": "invoices_list",
                "path": "/invoices",
                "method": "GET",
                "description": "List invoices with Stripe-compatible query params.",
            },
            {
                "name": "subscriptions_retrieve",
                "path": "/subscriptions/{subscription}",
                "method": "GET",
                "description": "Inspect recurring billing posture.",
            },
            {
                "name": "payment_intents_create",
                "path": "/payment_intents",
                "method": "POST",
                "description": "Stage PaymentIntents after human approvals.",
            },
            {
                "name": "customers_create",
                "path": "/customers",
                "method": "POST",
                "description": "Provision customer shells for external projects.",
            },
            {
                "name": "subscriptions_list",
                "path": "/subscriptions",
                "method": "GET",
                "description": "Enumerate subscriptions with Stripe-compatible filters.",
            },
            {
                "name": "invoices_retrieve",
                "path": "/invoices/{invoice}",
                "method": "GET",
                "description": "Hydrate invoice PDF/hosted URLs for ops review.",
            },
            {
                "name": "webhook_endpoints_list",
                "path": "/webhook_endpoints",
                "method": "GET",
                "description": "Verify signing secrets for Stripe ↔ External Projects bridges.",
            },
            {
                "name": "events_list",
                "path": "/events",
                "method": "GET",
                "description": "Audit recent webhook envelopes during reconciliation.",
            },
        ),
    ),
)


PHASE3_TEMPLATE_INDEX: dict[str, Phase3ConnectorTemplate] = {t.template_id: t for t in _PHASE3_RAW}


def iter_phase3_templates() -> tuple[Phase3ConnectorTemplate, ...]:
    """Stable ordering for APIs + dashboards."""

    return tuple(sorted(_PHASE3_RAW, key=lambda row: (row.category, row.title.lower())))


def get_phase3_template(template_id: str) -> Phase3ConnectorTemplate:
    """Resolve a preset or raise ``KeyError``."""

    key = template_id.strip()
    if key not in PHASE3_TEMPLATE_INDEX:
        msg = f"unknown_phase3_template:{template_id}"
        raise KeyError(msg)
    return PHASE3_TEMPLATE_INDEX[key]


def phase3_catalog_addon_lines() -> list[str]:
    """HiveMind / orchestrator appendix lines."""

    lines = [
        "### Phase 3 Communication & Knowledge templates",
        " Instantiate via `POST /api/v1/connectors/phase3/instantiate` then seal OAuth/API secrets.",
    ]
    for tpl in iter_phase3_templates():
        mgr = ",".join(tpl.suggested_manager_slugs) if tpl.suggested_manager_slugs else "*"
        lines.append(
            f"- `{tpl.template_id}` → slug `{tpl.suggested_slug}` ({tpl.category}) managers≈[{mgr}]",
        )
    return lines


def phase3_template_public_dict(tpl: Phase3ConnectorTemplate) -> dict[str, Any]:
    """JSON-serialisable projection for dashboards."""

    return {
        "template_id": tpl.template_id,
        "category": tpl.category,
        "title": tpl.title,
        "summary": tpl.summary,
        "documentation_url": tpl.documentation_url,
        "suggested_slug": tpl.suggested_slug,
        "auth_type": tpl.auth_type,
        "base_url": tpl.base_url,
        "suggested_manager_slugs": list(tpl.suggested_manager_slugs),
        "tools": [dict(tool) for tool in tpl.tools],
        "tool_count": len(tpl.tools),
    }


__all__ = [
    "PHASE3_TEMPLATE_INDEX",
    "Phase3ConnectorTemplate",
    "get_phase3_template",
    "iter_phase3_templates",
    "phase3_catalog_addon_lines",
    "phase3_template_public_dict",
]
