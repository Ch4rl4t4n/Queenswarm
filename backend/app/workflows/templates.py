"""Pre-built workflow shapes for Recipe Library seeding (Phase C)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.recipe import Recipe

logger = get_logger(__name__)

_SHARED_GUARD = {
    "risks": ["stale data", "provider outage"],
    "mitigations": ["retry with backoff", "cache recent pulls"],
    "stop_conditions": ["empty corpus after 3 attempts"],
}

_SHARED_EVAL = {
    "must_satisfy": ["structured JSON outputs", "confidence logged"],
    "measurable_signals": {"freshness_minutes": "<= 15"},
}

CRYPTO_ACKIE_WORKFLOW: dict[str, Any] = {
    "name": "CRYPTO_ACKIE",
    "description": "Crypto sentiment → evaluation → trade simulation → report.",
    "steps": [
        {
            "order": 1,
            "description": "Scrape YouTube crypto channels for sentiment snippets",
            "agent_role": "scraper",
            "input_schema": {"sources": "list[str]", "window_hours": "int"},
            "output_schema": {"clips": "list[{title, url, sentiment_score}]"},
            "guardrails": _SHARED_GUARD,
            "evaluation_criteria": _SHARED_EVAL,
        },
        {
            "order": 2,
            "description": "Evaluate scraped claims against exchange reference feeds",
            "agent_role": "evaluator",
            "input_schema": {"clips": "list"},
            "output_schema": {"verified_events": "list[dict]"},
            "guardrails": _SHARED_GUARD,
            "evaluation_criteria": _SHARED_EVAL,
        },
        {
            "order": 3,
            "description": "Simulate buy/hold/sell windows with sandboxed portfolio math",
            "agent_role": "simulator",
            "input_schema": {"portfolio": "dict", "horizon_days": "int"},
            "output_schema": {"paths": "list[dict]"},
            "guardrails": _SHARED_GUARD,
            "evaluation_criteria": _SHARED_EVAL,
        },
        {
            "order": 4,
            "description": "Generate trading analysis memo for hive operators",
            "agent_role": "reporter",
            "input_schema": {"paths": "list"},
            "output_schema": {"report_md": "str"},
            "guardrails": _SHARED_GUARD,
            "evaluation_criteria": _SHARED_EVAL,
        },
    ],
}

BLOG_POST_WORKFLOW: dict[str, Any] = {
    "name": "BLOG_POST",
    "description": "Research → outline → draft → publish checklist.",
    "steps": [
        {
            "order": 1,
            "description": "Scrape authoritative blogs for topic clusters",
            "agent_role": "scraper",
            "input_schema": {"topic": "str"},
            "output_schema": {"sources": "list[dict]"},
            "guardrails": _SHARED_GUARD,
            "evaluation_criteria": _SHARED_EVAL,
        },
        {
            "order": 2,
            "description": "Evaluate factual alignment of sources before drafting",
            "agent_role": "evaluator",
            "input_schema": {"sources": "list"},
            "output_schema": {"fact_sheet": "dict"},
            "guardrails": _SHARED_GUARD,
            "evaluation_criteria": _SHARED_EVAL,
        },
        {
            "order": 3,
            "description": "Simulate reader engagement for alternate headlines",
            "agent_role": "simulator",
            "input_schema": {"drafts": "list[str]"},
            "output_schema": {"winner": "str", "score": "float"},
            "guardrails": _SHARED_GUARD,
            "evaluation_criteria": _SHARED_EVAL,
        },
        {
            "order": 4,
            "description": "Compose markdown post and queue CMS publish",
            "agent_role": "blog_writer",
            "input_schema": {"fact_sheet": "dict", "headline": "str"},
            "output_schema": {"body_md": "str"},
            "guardrails": _SHARED_GUARD,
            "evaluation_criteria": _SHARED_EVAL,
        },
    ],
}

INSTAGRAM_POST_WORKFLOW: dict[str, Any] = {
    "name": "INSTAGRAM_POST",
    "description": "Visual brief → asset gather → copy simulate → schedule.",
    "steps": [
        {
            "order": 1,
            "description": "Scrape reference reels for visual language cues",
            "agent_role": "scraper",
            "input_schema": {"brand": "str"},
            "output_schema": {"moodboard": "list[dict]"},
            "guardrails": _SHARED_GUARD,
            "evaluation_criteria": _SHARED_EVAL,
        },
        {
            "order": 2,
            "description": "Evaluate caption claims for brand safety",
            "agent_role": "evaluator",
            "input_schema": {"captions": "list[str]"},
            "output_schema": {"approved": "list[str]"},
            "guardrails": _SHARED_GUARD,
            "evaluation_criteria": _SHARED_EVAL,
        },
        {
            "order": 3,
            "description": "Simulate engagement lift across posting times",
            "agent_role": "simulator",
            "input_schema": {"slots": "list[str]"},
            "output_schema": {"best_slot": "str"},
            "guardrails": _SHARED_GUARD,
            "evaluation_criteria": _SHARED_EVAL,
        },
    ],
}

YOUTUBE_DIGEST_WORKFLOW: dict[str, Any] = {
    "name": "YOUTUBE_DIGEST",
    "description": "Channel harvest → transcript QA → digest writers.",
    "steps": [
        {
            "order": 1,
            "description": "Scrape trending videos for specified channel list",
            "agent_role": "scraper",
            "input_schema": {"channels": "list[str]"},
            "output_schema": {"videos": "list[dict]"},
            "guardrails": _SHARED_GUARD,
            "evaluation_criteria": _SHARED_EVAL,
        },
        {
            "order": 2,
            "description": "Evaluate transcript quality and claims versus primary sources",
            "agent_role": "evaluator",
            "input_schema": {"videos": "list"},
            "output_schema": {"clean_items": "list[dict]"},
            "guardrails": _SHARED_GUARD,
            "evaluation_criteria": _SHARED_EVAL,
        },
        {
            "order": 3,
            "description": "Simulate newsletter sections ordering for readability",
            "agent_role": "simulator",
            "input_schema": {"sections": "list[str]"},
            "output_schema": {"ordering": "list[str]"},
            "guardrails": _SHARED_GUARD,
            "evaluation_criteria": _SHARED_EVAL,
        },
        {
            "order": 4,
            "description": "Publish digest copy + show notes for hive broadcast",
            "agent_role": "reporter",
            "input_schema": {"clean_items": "list"},
            "output_schema": {"digest_md": "str"},
            "guardrails": _SHARED_GUARD,
            "evaluation_criteria": _SHARED_EVAL,
        },
    ],
}

NEWSLETTER_WORKFLOW: dict[str, Any] = {
    "name": "NEWSLETTER",
    "description": "Audience scrape → tone eval → send simulation → HTML export.",
    "steps": [
        {
            "order": 1,
            "description": "Scrape subscriber segments and recent campaign replies",
            "agent_role": "scraper",
            "input_schema": {"segment": "str"},
            "output_schema": {"signals": "list[dict]"},
            "guardrails": _SHARED_GUARD,
            "evaluation_criteria": _SHARED_EVAL,
        },
        {
            "order": 2,
            "description": "Evaluate copy for CAN-SPAM facts and disclosures",
            "agent_role": "evaluator",
            "input_schema": {"draft_html": "str"},
            "output_schema": {"issues": "list[str]"},
            "guardrails": _SHARED_GUARD,
            "evaluation_criteria": _SHARED_EVAL,
        },
        {
            "order": 3,
            "description": "Simulate open-rate impact for subject line variants",
            "agent_role": "simulator",
            "input_schema": {"subjects": "list[str]"},
            "output_schema": {"winner": "str"},
            "guardrails": _SHARED_GUARD,
            "evaluation_criteria": _SHARED_EVAL,
        },
    ],
}

SEED_WORKFLOWS: dict[str, dict[str, Any]] = {
    "CRYPTO_ACKIE": CRYPTO_ACKIE_WORKFLOW,
    "BLOG_POST": BLOG_POST_WORKFLOW,
    "INSTAGRAM_POST": INSTAGRAM_POST_WORKFLOW,
    "YOUTUBE_DIGEST": YOUTUBE_DIGEST_WORKFLOW,
    "NEWSLETTER": NEWSLETTER_WORKFLOW,
}


async def load_seed_workflows(session: AsyncSession) -> int:
    """Insert bundled exemplar recipes when missing (idempotent).

    Args:
        session: Async SQLAlchemy session — caller commits.

    Returns:
        Count of newly inserted Recipe rows.
    """

    inserted = 0
    for _key, blob in SEED_WORKFLOWS.items():
        name = str(blob["name"])
        existing = await session.scalar(
            select(func.count()).select_from(Recipe).where(Recipe.name == name),
        )
        if existing and int(existing) > 0:
            continue
        template = {"seed_key": _key, "steps": blob.get("steps", [])}
        recipe = Recipe(
            name=name,
            description=str(blob.get("description") or ""),
            topic_tags=[_key.lower()],
            workflow_template=template,
            success_count=0,
            fail_count=0,
            avg_pollen_earned=0.0,
            embedding_id=None,
            created_by_agent_id=None,
            verified_at=None,
            last_used_at=None,
            is_deprecated=False,
        )
        session.add(recipe)
        inserted += 1
        logger.info("seed_workflow.inserted", recipe_name=name)

    if inserted:
        await session.flush()
    return inserted


__all__ = [
    "BLOG_POST_WORKFLOW",
    "CRYPTO_ACKIE_WORKFLOW",
    "INSTAGRAM_POST_WORKFLOW",
    "NEWSLETTER_WORKFLOW",
    "SEED_WORKFLOWS",
    "YOUTUBE_DIGEST_WORKFLOW",
    "load_seed_workflows",
]
