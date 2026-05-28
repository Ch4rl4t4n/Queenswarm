"""Marketplace card metadata for Phase 3 connector templates."""

from __future__ import annotations

from typing import Any, Literal

CostTier = Literal["low", "medium", "high"]
LatencyTier = Literal["fast", "balanced", "slow"]

# template_id → marketplace presentation (cost badges, agent guidance, external docs)
TEMPLATE_MARKETPLACE_META: dict[str, dict[str, Any]] = {
    "gmail_google_workspace": {
        "cost_tier": "medium",
        "latency_tier": "balanced",
        "agent_usage": (
            "Execution and content agents read threads, draft replies, and send verified mail once OAuth is sealed. "
            "Use for inbox triage, follow-ups, and Ballroom briefing attachments."
        ),
    },
    "outlook_microsoft365": {
        "cost_tier": "medium",
        "latency_tier": "balanced",
        "agent_usage": (
            "Enterprise mailbox lane — list messages, fetch bodies, and send via Microsoft Graph when OAuth is active. "
            "Pairs with review managers for approval-before-send flows."
        ),
    },
    "google_calendar": {
        "cost_tier": "low",
        "latency_tier": "fast",
        "agent_usage": (
            "Scheduling bees list events, create holds, and sync Ballroom follow-ups. "
            "Best for personal-life and execution lanes planning operator calendars."
        ),
    },
    "github_rest": {
        "cost_tier": "low",
        "latency_tier": "fast",
        "agent_usage": (
            "Coder and maintainer sub-agents open issues, inspect PRs, and comment after simulation. "
            "Use for repo health sweeps and release hygiene."
        ),
    },
    "gitlab_rest": {
        "cost_tier": "low",
        "latency_tier": "fast",
        "agent_usage": (
            "GitLab-native pipelines — merge requests, pipelines, and project metadata for DevOps execution lanes."
        ),
    },
    "slack_web_api": {
        "cost_tier": "low",
        "latency_tier": "fast",
        "agent_usage": (
            "Post verified updates to channels, read thread context, and react to operator alerts. "
            "Ideal for execution_operations broadcast after simulation passes."
        ),
    },
    "telegram_bot_api": {
        "cost_tier": "low",
        "latency_tier": "fast",
        "agent_usage": "Lightweight bot lane for mobile-friendly operator pings and async status cards.",
    },
    "discord_bot_api": {
        "cost_tier": "low",
        "latency_tier": "fast",
        "agent_usage": "Community and team alerts — send embeds and read channel history for support swarms.",
    },
    "notion_workspace": {
        "cost_tier": "medium",
        "latency_tier": "balanced",
        "agent_usage": (
            "Research and content agents search pages, append blocks, and export structured notes into HiveMind recipes."
        ),
    },
    "venice_mcp": {
        "cost_tier": "medium",
        "latency_tier": "balanced",
        "agent_usage": (
            "Privacy-first multimodal hop — chat, image, TTS, embeddings when Venice bearer token is configured. "
            "Content and research lanes; not a replacement for your primary LLM router."
        ),
    },
    "monid_mcp": {
        "cost_tier": "high",
        "latency_tier": "slow",
        "service_homepage": "https://monid.ai",
        "agent_usage": (
            "Deep external datasets on demand — discover → inspect → run paid endpoints (leads, social, sentiment). "
            "Enable only for verified research sessions; pause when idle to stop pay-per-call spend."
        ),
    },
    "composio_router": {
        "cost_tier": "medium",
        "latency_tier": "balanced",
        "auth_header_name": "x-api-key",
        "service_homepage": "https://composio.dev",
        "agent_usage": (
            "Unified app-action router — agents execute Composio tool slugs (Gmail, Slack, Salesforce, LinkedIn, etc.) "
            "via Tool Router sessions. Best when you need live actions across SaaS apps, not heavy scraping."
        ),
    },
    "apify_store": {
        "cost_tier": "high",
        "latency_tier": "slow",
        "service_homepage": "https://apify.com",
        "agent_usage": (
            "Heavy web scraping — run Apify Actors for Twitter, TikTok, e-commerce, Google SERP, and marketplace crawls. "
            "Research lane only; budget for compute/runtime charges per Actor run."
        ),
    },
    "nango_hub": {
        "cost_tier": "medium",
        "latency_tier": "balanced",
        "service_homepage": "https://nango.dev",
        "agent_usage": (
            "Managed OAuth + proxy hub for 800+ APIs — list connections then proxy GET/POST to CRM, HR, billing systems "
            "without bespoke auth code. Developer-first; pair with explicit Connection-Id per call."
        ),
    },
    "merge_agent_handler": {
        "cost_tier": "medium",
        "latency_tier": "balanced",
        "service_homepage": "https://merge.dev",
        "agent_usage": (
            "Enterprise unified categories (HR, accounting, CRM) via Merge Agent Handler MCP/REST. "
            "Agents list tool packs and invoke business-data tools after you register users and packs in Merge."
        ),
    },
    "instagram_graph_api": {
        "cost_tier": "medium",
        "latency_tier": "balanced",
        "service_homepage": "https://developers.facebook.com/docs/instagram-api",
        "agent_usage": (
            "Publish verified image/video posts to Instagram after Publish Queue approval. "
            "Simulate-first — live requires Meta Business OAuth and SOCIAL_PUBLISH_LIVE_ENABLED."
        ),
    },
    "facebook_graph_api": {
        "cost_tier": "medium",
        "latency_tier": "balanced",
        "service_homepage": "https://developers.facebook.com/docs/pages-api",
        "agent_usage": (
            "Post text and photo updates to Facebook Pages from approved publish packs. "
            "Use page_feed_publish for text-only; page_photo_publish when media_url is set."
        ),
    },
    "twitter_api_v2": {
        "cost_tier": "low",
        "latency_tier": "fast",
        "service_homepage": "https://developer.x.com",
        "agent_usage": (
            "Post tweets from verified publish packs — caption truncated to 280 chars. "
            "OAuth2 user context required for live posts."
        ),
    },
    "tiktok_content_posting": {
        "cost_tier": "medium",
        "latency_tier": "slow",
        "service_homepage": "https://developers.tiktok.com",
        "agent_usage": (
            "Publish short-form video via Content Posting API when publish pack includes video media_url. "
            "Poll publish_status_fetch after video_publish_init."
        ),
    },
    "resend_email_api": {
        "cost_tier": "low",
        "latency_tier": "fast",
        "service_homepage": "https://resend.com",
        "agent_usage": (
            "Send newsletter publish packs via Resend when Gmail OAuth is not used. "
            "Verify domain in Resend dashboard before live sends."
        ),
    },
    "polymarket_gamma_api": {
        "cost_tier": "low",
        "latency_tier": "fast",
        "service_homepage": "https://polymarket.com",
        "agent_usage": (
            "Discovery lane — list events/markets from Gamma API (no auth). "
            "Feed trading bot bees with token ids and outcome metadata."
        ),
    },
    "polymarket_clob_api": {
        "cost_tier": "high",
        "latency_tier": "balanced",
        "service_homepage": "https://docs.polymarket.com",
        "agent_usage": (
            "CLOB trading — order book, orders, placement. Requires L2 wallet credentials in Connector Vault. "
            "Order EIP-712 signing stays in your trading bot; Queenswarm proxies signed REST."
        ),
    },
    "kalshi_markets_api": {
        "cost_tier": "low",
        "latency_tier": "fast",
        "service_homepage": "https://kalshi.com",
        "agent_usage": (
            "Public Kalshi market data — browse tickers and order books before bot execution."
        ),
    },
    "kalshi_trading_api": {
        "cost_tier": "high",
        "latency_tier": "balanced",
        "service_homepage": "https://docs.kalshi.com",
        "agent_usage": (
            "Kalshi portfolio + orders via RSA-signed requests. "
            "Seal API Key ID + private PEM in Vault; simulate-first for order_create."
        ),
    },
}


def marketplace_meta_for(template_id: str) -> dict[str, Any]:
    """Return marketplace overlay for a template id."""

    return dict(TEMPLATE_MARKETPLACE_META.get(template_id.strip(), {}))


__all__ = ["TEMPLATE_MARKETPLACE_META", "marketplace_meta_for"]
