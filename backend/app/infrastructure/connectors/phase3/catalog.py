"""Canonical Phase 3 Communication & Knowledge connector templates.

Templates compile into :class:`~app.connectors.dynamic.schemas.DynamicConnectorCreateBody`
compatible MCP manifests executed by :func:`~app.connectors.dynamic.service.invoke_dynamic_tool`.

Upstream REST quirks (Slack JSON POST bodies, OAuth refresh, multi-part Gmail sends) remain
operator-owned — manifests encode the *happy-path* JSON surfaces Queenswarm can proxy today.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CategoryLiteral = Literal["email", "calendar", "devtools", "chat", "knowledge", "billing", "vault", "ai", "social", "trading"]
AuthLiteral = Literal["none", "api_key", "bearer_token", "oauth2", "polymarket_l2", "kalshi_rsa"]


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
                "name": "pulls_create",
                "path": "/repos/{owner}/{repo}/pulls",
                "method": "POST",
                "description": "Open a PR from queen-maintainer/* branch (Maintainer workflow).",
                "required_permission": "tool:write",
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
    Phase3ConnectorTemplate(
        template_id="venice_mcp",
        category="ai",
        title="Venice AI · MCP Hub",
        summary=(
            "OpenAI-compatible Venice API — chat, image generation, upscale, TTS, embeddings, "
            "and model discovery. One-click preset for privacy-first multimodal swarms."
        ),
        documentation_url="https://docs.venice.ai/api-reference/api-spec",
        suggested_slug="venice_mcp",
        auth_type="bearer_token",
        base_url="https://api.venice.ai/api/v1",
        suggested_manager_slugs=("content_creation", "research_intelligence", "optimization"),
        tools=(
            {
                "name": "chat_completions",
                "path": "/chat/completions",
                "method": "POST",
                "description": "Chat completions with Venice-hosted Llama, DeepSeek, Qwen, Mistral models.",
                "cost_tier": "medium",
                "latency_tier": "balanced",
            },
            {
                "name": "models_list",
                "path": "/models",
                "method": "GET",
                "description": "List available Venice chat, image, and embedding models.",
                "cost_tier": "low",
                "latency_tier": "fast",
            },
            {
                "name": "image_generate",
                "path": "/image/generate",
                "method": "POST",
                "description": "Generate images from text prompts (FLUX / SD families).",
                "cost_tier": "high",
                "latency_tier": "slow",
            },
            {
                "name": "image_upscale",
                "path": "/image/upscale",
                "method": "POST",
                "description": "Upscale and enhance generated or uploaded images.",
                "cost_tier": "medium",
                "latency_tier": "balanced",
            },
            {
                "name": "audio_speech",
                "path": "/audio/speech",
                "method": "POST",
                "description": "Text-to-speech for Ballroom voice briefings and alerts.",
                "cost_tier": "medium",
                "latency_tier": "balanced",
            },
            {
                "name": "embeddings_create",
                "path": "/embeddings",
                "method": "POST",
                "description": "Create embeddings for HiveMind vector lanes and tool routing.",
                "cost_tier": "low",
                "latency_tier": "fast",
            },
            {
                "name": "characters_list",
                "path": "/characters",
                "method": "GET",
                "description": "List Venice character personas for styled chat hops.",
                "cost_tier": "low",
                "latency_tier": "fast",
            },
            {
                "name": "rate_limits_get",
                "path": "/rate_limits",
                "method": "GET",
                "description": "Inspect Venice rate limits and usage for CostGovernor hints.",
                "cost_tier": "low",
                "latency_tier": "fast",
            },
            {
                "name": "web_search_chat",
                "path": "/chat/completions",
                "method": "POST",
                "description": "Web-augmented chat hop — pass venice_parameters for search-enabled models.",
                "cost_tier": "medium",
                "latency_tier": "balanced",
                "required_permission": "tool:write",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="monid_mcp",
        category="knowledge",
        title="Monid · Data Hub",
        summary=(
            "Pay-per-call agentic data layer — discover, inspect, and run 200+ external endpoints "
            "(leads, social, sentiment, competitor intel). Connect only when deep verified research is needed."
        ),
        documentation_url="https://docs.monid.ai/",
        suggested_slug="monid_mcp",
        auth_type="bearer_token",
        base_url="https://api.monid.ai/v1",
        suggested_manager_slugs=("research_intelligence", "execution_operations", "review_quality"),
        tools=(
            {
                "name": "discover",
                "path": "/discover",
                "method": "POST",
                "description": "Natural-language search for Monid endpoints (query, optional limit).",
                "cost_tier": "low",
                "latency_tier": "fast",
                "allowed_manager_slugs": ["research_intelligence", "execution_operations", "review_quality"],
            },
            {
                "name": "inspect",
                "path": "/inspect",
                "method": "POST",
                "description": "Fetch input schema, pricing, and docs for a provider+endpoint pair.",
                "cost_tier": "low",
                "latency_tier": "fast",
                "allowed_manager_slugs": ["research_intelligence", "execution_operations", "review_quality"],
            },
            {
                "name": "run",
                "path": "/run",
                "method": "POST",
                "description": "Execute a Monid endpoint (provider, endpoint, input). May return 202 — poll runs_get.",
                "cost_tier": "high",
                "latency_tier": "slow",
                "required_permission": "tool:write",
                "allowed_manager_slugs": ["research_intelligence", "execution_operations"],
            },
            {
                "name": "runs_get",
                "path": "/runs/{runId}",
                "method": "GET",
                "description": "Poll async Monid run status and output by runId.",
                "cost_tier": "low",
                "latency_tier": "fast",
                "allowed_manager_slugs": ["research_intelligence", "execution_operations", "review_quality"],
            },
            {
                "name": "runs_list",
                "path": "/runs",
                "method": "GET",
                "description": "List recent Monid runs (limit, cursor query params).",
                "cost_tier": "low",
                "latency_tier": "fast",
                "allowed_manager_slugs": ["research_intelligence", "review_quality"],
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="composio_router",
        category="devtools",
        title="Composio · Tool Router",
        summary=(
            "Unified agent action layer for 500+ SaaS apps — list tools, open Tool Router sessions, "
            "and execute slugs (Gmail, Slack, CRM, LinkedIn) with managed auth."
        ),
        documentation_url="https://docs.composio.dev/",
        suggested_slug="composio_router",
        auth_type="api_key",
        base_url="https://backend.composio.dev/api/v3.1",
        suggested_manager_slugs=("execution_operations", "research_intelligence", "content_creation"),
        tools=(
            {
                "name": "tools_list",
                "path": "/tools",
                "method": "GET",
                "description": "Search/list Composio tools (pass search, toolkit, limit as query args).",
                "cost_tier": "low",
                "latency_tier": "fast",
            },
            {
                "name": "tool_execute",
                "path": "/tools/execute/{tool_slug}",
                "method": "POST",
                "description": "Execute a Composio tool slug with JSON arguments + connected account id.",
                "cost_tier": "medium",
                "latency_tier": "balanced",
                "required_permission": "tool:write",
            },
            {
                "name": "tool_router_session_create",
                "path": "/tool_router/session/create",
                "method": "POST",
                "description": "Open a Tool Router session for autonomous multi-tool hops.",
                "cost_tier": "medium",
                "latency_tier": "balanced",
            },
            {
                "name": "tool_router_execute",
                "path": "/tool_router/session/{session_id}/execute",
                "method": "POST",
                "description": "Execute within an existing Tool Router session (session_id path arg).",
                "cost_tier": "medium",
                "latency_tier": "balanced",
                "required_permission": "tool:write",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="apify_store",
        category="knowledge",
        title="Apify · Scraper Store",
        summary=(
            "Thousands of web scrapers and crawlers as Actors — Twitter, TikTok, Google, e-commerce, "
            "and SERP harvesters with async run polling."
        ),
        documentation_url="https://docs.apify.com/api/v2",
        suggested_slug="apify_store",
        auth_type="bearer_token",
        base_url="https://api.apify.com/v2",
        suggested_manager_slugs=("research_intelligence", "execution_operations"),
        tools=(
            {
                "name": "actors_list",
                "path": "/acts",
                "method": "GET",
                "description": "List/store-search Apify Actors (my, limit, offset query params).",
                "cost_tier": "low",
                "latency_tier": "fast",
            },
            {
                "name": "actor_run",
                "path": "/acts/{actorId}/runs",
                "method": "POST",
                "description": "Start an Actor run asynchronously (actorId path + JSON input body).",
                "cost_tier": "high",
                "latency_tier": "slow",
                "required_permission": "tool:write",
            },
            {
                "name": "actor_run_get",
                "path": "/acts/{actorId}/runs/{runId}",
                "method": "GET",
                "description": "Poll Actor run status and stats.",
                "cost_tier": "low",
                "latency_tier": "fast",
            },
            {
                "name": "actor_run_sync",
                "path": "/acts/{actorId}/run-sync",
                "method": "POST",
                "description": "Run Actor synchronously when output must return in one hop (300s cap).",
                "cost_tier": "high",
                "latency_tier": "slow",
                "required_permission": "tool:write",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="nango_hub",
        category="devtools",
        title="Nango · Auth Proxy Hub",
        summary=(
            "Managed OAuth vault plus HTTP proxy for 800+ integrations — list connections, "
            "then proxy GET/POST to CRM, HR, and billing APIs with sealed tokens."
        ),
        documentation_url="https://nango.dev/docs",
        suggested_slug="nango_hub",
        auth_type="bearer_token",
        base_url="https://api.nango.dev",
        suggested_manager_slugs=("execution_operations", "review_quality"),
        tools=(
            {
                "name": "connections_list",
                "path": "/connection",
                "method": "GET",
                "description": "List synced Nango connections for the environment.",
                "cost_tier": "low",
                "latency_tier": "fast",
            },
            {
                "name": "proxy_get",
                "path": "/proxy/{proxy_path}",
                "method": "GET",
                "description": "Authenticated GET proxy — include Connection-Id + Provider-Config-Key via hub manifest headers.",
                "cost_tier": "medium",
                "latency_tier": "balanced",
            },
            {
                "name": "proxy_post",
                "path": "/proxy/{proxy_path}",
                "method": "POST",
                "description": "Authenticated POST proxy for mutating upstream APIs.",
                "cost_tier": "medium",
                "latency_tier": "balanced",
                "required_permission": "tool:write",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="merge_agent_handler",
        category="billing",
        title="Merge · Agent Handler",
        summary=(
            "Unified business-data MCP/REST for HR, accounting, and CRM categories — "
            "list tool packs and invoke MCP JSON-RPC tools for registered users."
        ),
        documentation_url="https://docs.merge.dev/merge-agent-handler/",
        suggested_slug="merge_agent_handler",
        auth_type="bearer_token",
        base_url="https://ah-api.merge.dev/api/v1",
        suggested_manager_slugs=("execution_operations", "review_quality", "research_intelligence"),
        tools=(
            {
                "name": "tool_packs_list",
                "path": "/tool-packs",
                "method": "GET",
                "description": "List Merge Agent Handler tool packs available to the workspace.",
                "cost_tier": "low",
                "latency_tier": "fast",
            },
            {
                "name": "registered_users_list",
                "path": "/registered-users",
                "method": "GET",
                "description": "List registered users entitled to tool-pack MCP access.",
                "cost_tier": "low",
                "latency_tier": "fast",
            },
            {
                "name": "mcp_tools_call",
                "path": "/tool-packs/{tool_pack_id}/registered-users/{registered_user_id}/mcp",
                "method": "POST",
                "description": "JSON-RPC MCP hop — pass method/tools/call payload in JSON body.",
                "cost_tier": "medium",
                "latency_tier": "balanced",
                "required_permission": "tool:write",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="instagram_graph_api",
        category="social",
        title="Instagram · Meta Graph",
        summary=(
            "Publish feed posts and Reels via Instagram Graph API. OAuth2 via Meta Business/Creator account. "
            "Use media container → publish flow; default Execution Studio policy is simulate until operator approves live."
        ),
        documentation_url="https://developers.facebook.com/docs/instagram-api/guides/content-publishing",
        suggested_slug="instagram_graph",
        auth_type="oauth2",
        base_url="https://graph.facebook.com/v21.0",
        suggested_manager_slugs=("content_creation", "execution_operations"),
        tools=(
            {
                "name": "ig_user_profile",
                "path": "/{ig_user_id}",
                "method": "GET",
                "description": "Fetch IG user profile metadata (requires instagram_basic scope).",
            },
            {
                "name": "media_create",
                "path": "/{ig_user_id}/media",
                "method": "POST",
                "description": "Create media container — JSON `{image_url, caption}` or `{video_url, caption, media_type}`.",
                "required_permission": "tool:write",
            },
            {
                "name": "media_publish",
                "path": "/{ig_user_id}/media_publish",
                "method": "POST",
                "description": "Publish container — JSON `{creation_id}` from media_create response.",
                "required_permission": "tool:write",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="facebook_graph_api",
        category="social",
        title="Facebook · Meta Graph Pages",
        summary=(
            "Publish text, link, and photo posts to Facebook Pages via Graph API. "
            "Pair with verified publish packs — simulate-first until live toggle + operator approval."
        ),
        documentation_url="https://developers.facebook.com/docs/pages-api/posts",
        suggested_slug="facebook_graph",
        auth_type="oauth2",
        base_url="https://graph.facebook.com/v21.0",
        suggested_manager_slugs=("content_creation", "execution_operations"),
        tools=(
            {
                "name": "page_list",
                "path": "/me/accounts",
                "method": "GET",
                "description": "List managed Pages and page access tokens.",
            },
            {
                "name": "page_feed_publish",
                "path": "/{page_id}/feed",
                "method": "POST",
                "description": "Publish text/link post — JSON `{message, link}` from publish pack body.",
                "required_permission": "tool:write",
            },
            {
                "name": "page_photo_publish",
                "path": "/{page_id}/photos",
                "method": "POST",
                "description": "Publish photo post — JSON `{url, caption}` when media_url present.",
                "required_permission": "tool:write",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="twitter_api_v2",
        category="social",
        title="X (Twitter) · API v2",
        summary=(
            "Post tweets with optional media via X API v2. OAuth2 user context recommended. "
            "Compose caption from publish pack; live posts require operator approval in Execution Studio."
        ),
        documentation_url="https://developer.x.com/en/docs/twitter-api/tweets/manage-tweets/api-reference/post-tweets",
        suggested_slug="twitter_api_v2",
        auth_type="oauth2",
        base_url="https://api.twitter.com",
        suggested_manager_slugs=("content_creation", "execution_operations"),
        tools=(
            {
                "name": "tweets_create",
                "path": "/2/tweets",
                "method": "POST",
                "description": "Create tweet — JSON `{text}` up to 280 chars; optional media_ids from upload.",
                "required_permission": "tool:write",
            },
            {
                "name": "users_me",
                "path": "/2/users/me",
                "method": "GET",
                "description": "Verify OAuth credentials and resolve authenticated user id.",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="tiktok_content_posting",
        category="social",
        title="TikTok · Content Posting API",
        summary=(
            "Init and publish short-form video to TikTok via Content Posting API. "
            "Requires video_url from publish pack media; caption in post_info.title/description fields."
        ),
        documentation_url="https://developers.tiktok.com/doc/content-posting-api-get-started",
        suggested_slug="tiktok_content",
        auth_type="oauth2",
        base_url="https://open.tiktokapis.com/v2",
        suggested_manager_slugs=("content_creation", "execution_operations"),
        tools=(
            {
                "name": "creator_info",
                "path": "/post/publish/creator_info/query/",
                "method": "POST",
                "description": "Query creator publishing capabilities and privacy options.",
            },
            {
                "name": "video_publish_init",
                "path": "/post/publish/video/init/",
                "method": "POST",
                "description": "Init direct-post video publish — JSON post_info + source_info with video_url.",
                "required_permission": "tool:write",
            },
            {
                "name": "publish_status_fetch",
                "path": "/post/publish/status/fetch/",
                "method": "POST",
                "description": "Poll publish_id status after video_publish_init.",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="polymarket_gamma_api",
        category="trading",
        title="Polymarket · Gamma (markets)",
        summary=(
            "Public market metadata from Polymarket Gamma API — events, markets, outcomes. "
            "No auth required; use for research bees and trading bot signal discovery."
        ),
        documentation_url="https://docs.polymarket.com/quickstart",
        suggested_slug="polymarket_gamma",
        auth_type="none",
        base_url="https://gamma-api.polymarket.com",
        suggested_manager_slugs=("research_intelligence", "execution_operations"),
        tools=(
            {
                "name": "markets_list",
                "path": "/markets",
                "method": "GET",
                "description": "List active markets — optional query limit, closed, tag filters.",
                "cost_tier": "low",
                "latency_tier": "fast",
            },
            {
                "name": "events_list",
                "path": "/events",
                "method": "GET",
                "description": "List events with nested markets for discovery.",
                "cost_tier": "low",
                "latency_tier": "fast",
            },
            {
                "name": "market_get",
                "path": "/markets/{slug}",
                "method": "GET",
                "description": "Fetch one market by slug or id path param.",
                "cost_tier": "low",
                "latency_tier": "fast",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="polymarket_clob_api",
        category="trading",
        title="Polymarket · CLOB (trading)",
        summary=(
            "Central limit order book — order book, mid prices, orders. "
            "Requires L2 API credentials derived from your Polygon wallet. "
            "Simulate-first: live order placement needs operator approval + trading bot lane."
        ),
        documentation_url="https://docs.polymarket.com/api-reference/authentication",
        suggested_slug="polymarket_clob",
        auth_type="polymarket_l2",
        base_url="https://clob.polymarket.com",
        suggested_manager_slugs=("execution_operations", "research_intelligence"),
        tools=(
            {
                "name": "orderbook_get",
                "path": "/book",
                "method": "GET",
                "description": "Order book for token_id query param.",
                "cost_tier": "low",
                "latency_tier": "fast",
            },
            {
                "name": "midpoint_get",
                "path": "/midpoint",
                "method": "GET",
                "description": "Mid price for token_id query param.",
                "cost_tier": "low",
                "latency_tier": "fast",
            },
            {
                "name": "orders_list",
                "path": "/data/orders",
                "method": "GET",
                "description": "List open orders for authenticated wallet.",
                "cost_tier": "medium",
                "latency_tier": "balanced",
            },
            {
                "name": "order_post",
                "path": "/order",
                "method": "POST",
                "description": "Place order — requires signed order payload from trading bot (EIP-712).",
                "required_permission": "tool:write",
                "cost_tier": "high",
                "latency_tier": "balanced",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="kalshi_markets_api",
        category="trading",
        title="Kalshi · Markets (public)",
        summary=(
            "Public Kalshi market data — browse events, order books, and trades. "
            "No auth for read endpoints; pair with kalshi_trading for portfolio actions."
        ),
        documentation_url="https://docs.kalshi.com/getting_started/quick_start_market_data",
        suggested_slug="kalshi_markets",
        auth_type="none",
        base_url="https://api.elections.kalshi.com/trade-api/v2",
        suggested_manager_slugs=("research_intelligence", "execution_operations"),
        tools=(
            {
                "name": "markets_list",
                "path": "/markets",
                "method": "GET",
                "description": "List markets — status, series, limit query params.",
                "cost_tier": "low",
                "latency_tier": "fast",
            },
            {
                "name": "market_get",
                "path": "/markets/{ticker}",
                "method": "GET",
                "description": "Fetch one market by ticker.",
                "cost_tier": "low",
                "latency_tier": "fast",
            },
            {
                "name": "orderbook_get",
                "path": "/markets/{ticker}/orderbook",
                "method": "GET",
                "description": "Market order book depth.",
                "cost_tier": "low",
                "latency_tier": "fast",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="kalshi_trading_api",
        category="trading",
        title="Kalshi · Trading (RSA)",
        summary=(
            "Authenticated Kalshi trading — balance, positions, orders. "
            "RSA-PSS signed requests with API Key ID + private key from Kalshi profile. "
            "Simulate-first until operator enables live prediction-market trading."
        ),
        documentation_url="https://docs.kalshi.com/getting_started/api_keys",
        suggested_slug="kalshi_trading",
        auth_type="kalshi_rsa",
        base_url="https://api.elections.kalshi.com/trade-api/v2",
        suggested_manager_slugs=("execution_operations",),
        tools=(
            {
                "name": "balance_get",
                "path": "/portfolio/balance",
                "method": "GET",
                "description": "Portfolio cash balance — use as Connector Hub ping target.",
                "cost_tier": "low",
                "latency_tier": "fast",
            },
            {
                "name": "positions_list",
                "path": "/portfolio/positions",
                "method": "GET",
                "description": "Open positions for the authenticated account.",
                "cost_tier": "low",
                "latency_tier": "fast",
            },
            {
                "name": "orders_list",
                "path": "/portfolio/orders",
                "method": "GET",
                "description": "List resting and recent orders.",
                "cost_tier": "medium",
                "latency_tier": "balanced",
            },
            {
                "name": "order_create",
                "path": "/portfolio/orders",
                "method": "POST",
                "description": "Create order — JSON ticker, side, count, yes_price (cents). Operator confirm for live.",
                "required_permission": "tool:write",
                "cost_tier": "high",
                "latency_tier": "balanced",
            },
        ),
    ),
    Phase3ConnectorTemplate(
        template_id="resend_email_api",
        category="email",
        title="Resend · Transactional Email",
        summary=(
            "Send newsletter and transactional email via Resend API. "
            "Alternative to Gmail for publish packs with channel=newsletter."
        ),
        documentation_url="https://resend.com/docs/api-reference/emails/send-email",
        suggested_slug="resend_email",
        auth_type="bearer_token",
        base_url="https://api.resend.com",
        suggested_manager_slugs=("content_creation", "execution_operations"),
        tools=(
            {
                "name": "emails_send",
                "path": "/emails",
                "method": "POST",
                "description": "Send email — JSON `{from, to, subject, html}` from publish pack body.",
                "required_permission": "tool:write",
            },
            {
                "name": "domains_list",
                "path": "/domains",
                "method": "GET",
                "description": "List verified sending domains.",
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
