"""Tenant-scoped Hive Mind recall mode (full vs selective graph-neighbor RAG)."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.tenant_context import get_current_tenant_uuid
from app.infrastructure.persistence.models.tenant import Tenant

RecallMode = Literal["full", "selective"]

RECALL_BUCKET = "hive_mind_recall"
DEFAULT_RECALL_MODE: RecallMode = "selective"

logger = get_logger(__name__)


def normalize_recall_mode(raw: object) -> RecallMode:
    """Coerce stored value to supported recall mode."""

    text = str(raw or DEFAULT_RECALL_MODE).strip().lower()
    if text in {"full", "selective"}:
        return text  # type: ignore[return-value]
    return DEFAULT_RECALL_MODE


def _recall_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get(RECALL_BUCKET)
    return dict(bucket) if isinstance(bucket, dict) else {}


def recall_config_from_tenant(tenant: Tenant | None) -> dict[str, Any]:
    """Read recall config from tenant operator_settings."""

    bucket = _recall_bucket(tenant.operator_settings if tenant is not None else None)
    return {
        "recall_mode": normalize_recall_mode(bucket.get("recall_mode")),
        "token_budget_chars": int(bucket.get("token_budget_chars") or 0),
    }


async def load_recall_config(session: AsyncSession, *, tenant_id: object | None = None) -> dict[str, Any]:
    """Load effective recall config for tenant."""

    if not settings.hive_mind_selective_recall_enabled:
        return {
            "recall_mode": "full",
            "token_budget_chars": 0,
            "feature_enabled": False,
        }

    resolved_id = tenant_id or get_current_tenant_uuid()
    if resolved_id is None:
        return {
            "recall_mode": DEFAULT_RECALL_MODE,
            "token_budget_chars": 0,
            "feature_enabled": True,
        }

    tenant = await session.get(Tenant, resolved_id)
    cfg = recall_config_from_tenant(tenant)
    cfg["feature_enabled"] = True
    return cfg


def merge_recall_patch(operator_settings: dict[str, Any] | None, patch: dict[str, Any]) -> dict[str, Any]:
    """Apply partial hive_mind_recall patch."""

    root = dict(operator_settings or {})
    bucket = _recall_bucket(root)
    if "recall_mode" in patch:
        bucket["recall_mode"] = normalize_recall_mode(patch["recall_mode"])
    if "token_budget_chars" in patch:
        raw = patch["token_budget_chars"]
        bucket["token_budget_chars"] = max(0, int(raw or 0))
    root[RECALL_BUCKET] = bucket
    return root


def score_vector_similarity(distance: object) -> float:
    """Convert vector distance to similarity score in [0, 1]."""

    try:
        dist = float(distance)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, 1.0 - dist))


def rank_vector_hits(
    hits: list[dict[str, Any]],
    *,
    max_hits: int,
    min_similarity: float,
) -> tuple[list[dict[str, Any]], int]:
    """Rank vector hits by similarity and prune weak matches."""

    ranked: list[tuple[float, dict[str, Any]]] = []
    for hit in hits:
        sim = score_vector_similarity(hit.get("distance"))
        if sim < min_similarity:
            continue
        ranked.append((sim, {**hit, "similarity": sim}))

    ranked.sort(key=lambda pair: pair[0], reverse=True)
    kept = [item for _, item in ranked[: max(1, max_hits)]]
    pruned = max(0, len(hits) - len(kept))
    return kept, pruned


def effective_prompt_char_budget(
    *,
    recall_mode: RecallMode,
    tenant_budget: int,
    settings_max_prompt: int,
    selective_max_chars: int,
) -> int:
    """Resolve char budget for recall block assembly."""

    if recall_mode == "full":
        return settings_max_prompt
    if tenant_budget > 0:
        return min(tenant_budget, settings_max_prompt)
    return min(selective_max_chars, settings_max_prompt)


def query_tokens(query: str) -> set[str]:
    """Tokenize query for lightweight vault overlap scoring."""

    return {token.strip().lower() for token in query.split() if len(token.strip()) >= 3}


__all__ = [
    "DEFAULT_RECALL_MODE",
    "RECALL_BUCKET",
    "RecallMode",
    "effective_prompt_char_budget",
    "load_recall_config",
    "merge_recall_patch",
    "normalize_recall_mode",
    "query_tokens",
    "rank_vector_hits",
    "recall_config_from_tenant",
    "score_vector_similarity",
]
