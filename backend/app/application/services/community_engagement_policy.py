"""POS-CE — Community engagement policy (collect → compose → commit with HITL)."""

from __future__ import annotations

import re
from typing import Any, Final

COMMUNITY_ENGAGEMENT_HARNESS_MARKER: Final[str] = "## Community Engagement (POS-CE)"

COMMUNITY_AUTHENTICITY_RUBRIC_ID: Final[str] = "community-authenticity"

DEFAULT_MAX_DRAFT_REPLIES_PER_DIGEST: Final[int] = 3
DEFAULT_MAX_LIVE_POSTS_PER_DAY: Final[int] = 0

_REDDIT_SUB_RE: Final[re.Pattern[str]] = re.compile(
    r"reddit\.com/r/([A-Za-z0-9_]+)",
    re.IGNORECASE,
)

COMMUNITY_ENGAGEMENT_LANE_CONTEXT: Final[dict[str, Any]] = {
    "community_engagement": {
        "enabled": True,
        "max_draft_replies_per_digest": DEFAULT_MAX_DRAFT_REPLIES_PER_DIGEST,
        "max_live_posts_per_day": DEFAULT_MAX_LIVE_POSTS_PER_DAY,
        "closed_review_template_id": COMMUNITY_AUTHENTICITY_RUBRIC_ID,
        "simulate_only": True,
    },
}

COMMUNITY_MONITOR_SKILL_BUNDLE: Final[list[str]] = [
    "community-engagement-playbook",
    "competitor-scrape-analyze",
    "context",
    "closed-review-loop",
]

COMMUNITY_FORAGER_PROMPT: Final[str] = """\
Use skill community-engagement-playbook for downstream drafts.

For each ingested post/thread:
- Tag Knowledge rows: engagement-candidate, community-intel, pending-review.
- Extract: platform, thread URL, question/intent, community tone hints.
- Never auto-post. Never tag hivemind-candidate without operator path.
- Default simulate-only; live outbound requires operator-approval-gate.
"""

COMMUNITY_HARNESS_BLOCK: Final[str] = """\
## Community Engagement (POS-CE)

**Collect → compose → commit (HITL).** No autonomous live posting on Reddit/forums.

### Flow
1. **Forager** (RSS Reddit / Discovery / RSS forums) → Knowledge tagged `engagement-candidate`.
2. **Marketing digest** or procedure `/community-engage` → draft helpful replies (max 3/digest).
3. **Closed review loop** with rubric `community-authenticity` (helpfulness before promo).
4. **Publish queue simulate** → operator approve in Tasks / BA4 inbox.
5. **Live post** only when connector enabled + daily cap respected.

### Combine with
- Four Lane **marketing_najman** digest (CZ brand voice)
- **social-intel-evaluator** for inbound intel only (not outbound)
- **competitor-scrape-analyze** for forum context
- **Data Monitor wizard** — intent with subreddit URLs
- **Goldmine alerts** → Kanban dispatch with skill bundle

### Stop rules
- max_draft_replies_per_digest: 3
- max_live_posts_per_day: 0 (simulate until operator raises cap)
- same-failure-twice → needs_input (LOOP2 / LN1)
"""


def reddit_urls_to_rss_feeds(text: str) -> list[str]:
    """Convert reddit.com/r/sub URLs to public .rss feed URLs."""

    feeds: list[str] = []
    seen: set[str] = set()
    for match in _REDDIT_SUB_RE.finditer(text):
        sub = match.group(1).lower()
        feed = f"https://www.reddit.com/r/{sub}/.rss"
        if feed not in seen:
            seen.add(feed)
            feeds.append(feed)
    return feeds


def merge_community_engagement_context(context_payload: dict[str, Any] | None) -> dict[str, Any]:
    """Merge POS-CE lane defaults into supervisor routine context."""

    merged = dict(context_payload or {})
    ce = dict(merged.get("community_engagement") or {})
    defaults = dict(COMMUNITY_ENGAGEMENT_LANE_CONTEXT["community_engagement"])
    for key, value in defaults.items():
        ce.setdefault(key, value)
    merged["community_engagement"] = ce
    return merged


def monitor_skill_bundle(*, niche: str, source_type: str) -> list[str]:
    """Return skill bundle for data monitor wizard plans."""

    if niche == "community":
        return list(COMMUNITY_MONITOR_SKILL_BUNDLE)
    from app.application.services.forager_goldmine_dispatch_service import derive_forager_skill_bundle

    return derive_forager_skill_bundle(source_type)


__all__ = [
    "COMMUNITY_AUTHENTICITY_RUBRIC_ID",
    "COMMUNITY_ENGAGEMENT_HARNESS_MARKER",
    "COMMUNITY_ENGAGEMENT_LANE_CONTEXT",
    "COMMUNITY_FORAGER_PROMPT",
    "COMMUNITY_HARNESS_BLOCK",
    "COMMUNITY_MONITOR_SKILL_BUNDLE",
    "DEFAULT_MAX_DRAFT_REPLIES_PER_DIGEST",
    "merge_community_engagement_context",
    "monitor_skill_bundle",
    "reddit_urls_to_rss_feeds",
]
