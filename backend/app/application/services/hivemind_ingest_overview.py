"""HiveMind ingest dashboard — answers "is the Quality Contract actually working?".

Pulls four signals into one operator-facing payload:

1. VaultDocument counts in Neo4j (the Auto-Graphify pipeline output —
   this is where every successful `[INSIGHT]` Notion page lands).
2. Top tags across recent VaultDocuments (so we can see whether agents
   are tagging `hivemind-candidate` and the domain-specific axes).
3. Dump-and-sleep queue health (Postgres) — how many overnight batches
   are stuck in QUEUED/PROCESSING vs. COMPLETED.
4. Dream insight counts (Postgres) — supplementary signal from the
   overnight reasoning loop.

Why this matters
----------------
Without this panel we cannot tell whether the new agent system prompts
(HIVEMIND DUTY + CROSS-CHECK PROTOCOL) translate into actual HiveMind growth.
This service is the closed-loop feedback for the quality contract.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.neo4j_client import get_neo4j_driver
from app.infrastructure.persistence.models.dream_cycle import DreamInsightORM
from app.infrastructure.persistence.models.dump_sleep_batch import (
    DumpSleepBatchORM,
    DumpSleepStatusORM,
)


_HIVEMIND_TAG = "hivemind-candidate"
_DEFAULT_WINDOW_HOURS = 24


async def _vault_document_stats(
    tenant_id: uuid.UUID,
    *,
    window_hours: int,
) -> dict[str, Any]:
    """Return Neo4j VaultDocument counts + top tag breakdown for the window."""

    driver = await get_neo4j_driver()
    tid = str(tenant_id)
    cutoff_iso = (datetime.now(tz=UTC) - timedelta(hours=window_hours)).isoformat()

    stats: dict[str, Any] = {
        "total_last_window": 0,
        "with_hivemind_tag": 0,
        "tags_top": [],
        "lag": {"oldest_pending_iso": None, "pending_count": 0},
        "samples": [],
    }

    async with driver.session(database="neo4j") as session:
        cursor = await session.run(
            """
            MATCH (d:VaultDocument {tenant_id: $tid})
            WHERE d.updated_at >= datetime($cutoff)
            RETURN count(d) AS total,
                   sum(CASE WHEN $hm IN coalesce(d.tags, []) THEN 1 ELSE 0 END) AS with_hm
            """,
            tid=tid,
            cutoff=cutoff_iso,
            hm=_HIVEMIND_TAG,
        )
        row = await cursor.single()
        if row is not None:
            stats["total_last_window"] = int(row.get("total") or 0)
            stats["with_hivemind_tag"] = int(row.get("with_hm") or 0)

        cursor = await session.run(
            """
            MATCH (d:VaultDocument {tenant_id: $tid})-[:TAGGED_AS]->(tg:Tag)
            WHERE d.updated_at >= datetime($cutoff)
            RETURN tg.name AS tag, count(d) AS hits
            ORDER BY hits DESC LIMIT 12
            """,
            tid=tid,
            cutoff=cutoff_iso,
        )
        stats["tags_top"] = [
            {"tag": rec.get("tag"), "hits": int(rec.get("hits") or 0)}
            async for rec in cursor
            if rec.get("tag")
        ]

        cursor = await session.run(
            """
            MATCH (d:VaultDocument {tenant_id: $tid})
            WHERE d.updated_at >= datetime($cutoff)
            RETURN d.doc_id AS doc_id,
                   d.title AS title,
                   d.tags  AS tags,
                   toString(d.updated_at) AS updated_at
            ORDER BY d.updated_at DESC LIMIT 5
            """,
            tid=tid,
            cutoff=cutoff_iso,
        )
        stats["samples"] = [
            {
                "doc_id": rec.get("doc_id"),
                "title": rec.get("title"),
                "tags": list(rec.get("tags") or [])[:8],
                "updated_at": rec.get("updated_at"),
            }
            async for rec in cursor
        ]

    return stats


async def _dump_sleep_stats(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    window_hours: int,
) -> dict[str, Any]:
    """Return dump-and-sleep batch health for the operator's tenant."""

    cutoff = datetime.now(tz=UTC) - timedelta(hours=window_hours)
    by_status: dict[str, int] = {}

    for status in DumpSleepStatusORM:
        count = int(
            await db.scalar(
                select(func.count())
                .select_from(DumpSleepBatchORM)
                .where(
                    DumpSleepBatchORM.tenant_id == tenant_id,
                    DumpSleepBatchORM.created_at >= cutoff,
                    DumpSleepBatchORM.status == status,
                )
            )
            or 0
        )
        by_status[status.value] = count

    pending_count = int(
        await db.scalar(
            select(func.count())
            .select_from(DumpSleepBatchORM)
            .where(
                DumpSleepBatchORM.tenant_id == tenant_id,
                DumpSleepBatchORM.status.in_(
                    [DumpSleepStatusORM.QUEUED, DumpSleepStatusORM.PROCESSING]
                ),
            )
        )
        or 0
    )

    oldest_pending = await db.scalar(
        select(func.min(DumpSleepBatchORM.created_at)).where(
            DumpSleepBatchORM.tenant_id == tenant_id,
            DumpSleepBatchORM.status.in_(
                [DumpSleepStatusORM.QUEUED, DumpSleepStatusORM.PROCESSING]
            ),
        )
    )

    return {
        "by_status": by_status,
        "pending_count": pending_count,
        "oldest_pending_at": oldest_pending.isoformat() if oldest_pending else None,
    }


async def _dream_insight_stats(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    window_hours: int,
) -> dict[str, Any]:
    """Return dream insight counts for the window."""

    cutoff = datetime.now(tz=UTC) - timedelta(hours=window_hours)
    count = int(
        await db.scalar(
            select(func.count())
            .select_from(DreamInsightORM)
            .where(
                DreamInsightORM.tenant_id == tenant_id,
                DreamInsightORM.created_at >= cutoff,
            )
        )
        or 0
    )
    latest = await db.scalar(
        select(func.max(DreamInsightORM.created_at)).where(
            DreamInsightORM.tenant_id == tenant_id,
        )
    )
    return {
        "count_last_window": count,
        "latest_at": latest.isoformat() if latest else None,
    }


def _quality_signal(vault: dict[str, Any]) -> str:
    """Coarse health label: green / amber / red."""

    total = int(vault.get("total_last_window") or 0)
    tagged = int(vault.get("with_hivemind_tag") or 0)
    if total == 0:
        return "red"
    tagged_ratio = tagged / total if total else 0
    if total >= 5 and tagged_ratio >= 0.5:
        return "green"
    if total >= 2:
        return "amber"
    return "amber"


async def build_hivemind_ingest_overview(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    window_hours: int | None = None,
) -> dict[str, Any]:
    """Build the operator dashboard payload for HiveMind growth + quality."""

    window = max(1, min(int(window_hours or _DEFAULT_WINDOW_HOURS), 720))
    vault = await _vault_document_stats(tenant_id, window_hours=window)
    dump = await _dump_sleep_stats(db, tenant_id=tenant_id, window_hours=window)
    dreams = await _dream_insight_stats(db, tenant_id=tenant_id, window_hours=window)

    signal = _quality_signal(vault)
    contract_compliance_pct: float | None
    if vault["total_last_window"]:
        contract_compliance_pct = round(
            vault["with_hivemind_tag"] / vault["total_last_window"] * 100, 1
        )
    else:
        contract_compliance_pct = None

    headline = {
        "vault_documents_last_window": vault["total_last_window"],
        "hivemind_candidate_pages": vault["with_hivemind_tag"],
        "contract_compliance_pct": contract_compliance_pct,
        "dump_pending": dump["pending_count"],
        "dream_insights_last_window": dreams["count_last_window"],
        "quality_signal": signal,
    }

    return {
        "window_hours": window,
        "as_of": datetime.now(tz=UTC).isoformat(),
        "headline": headline,
        "vault_documents": vault,
        "dump_sleep": dump,
        "dream_insights": dreams,
        "notes": _operator_notes(headline),
    }


def _operator_notes(headline: dict[str, Any]) -> list[str]:
    """Short, headed advisories for the operator panel."""

    notes: list[str] = []
    total = int(headline.get("vault_documents_last_window") or 0)
    tagged = int(headline.get("hivemind_candidate_pages") or 0)
    dump_pending = int(headline.get("dump_pending") or 0)
    compliance = headline.get("contract_compliance_pct")

    if total == 0:
        notes.append(
            "No new VaultDocuments in window — no agent has yet written a "
            "[INSIGHT] page. Either no swarm has run, or Auto-Graphify is "
            "blocked on Notion."
        )
    elif compliance is not None and compliance < 50:
        notes.append(
            f"HiveMind Quality Contract compliance is {compliance:.0f}% — "
            "less than half of recent pages carry the `hivemind-candidate` tag. "
            "Agent prompts may need a re-seed."
        )
    elif compliance is not None and compliance >= 80:
        notes.append(
            f"HiveMind Quality Contract compliance is healthy ({compliance:.0f}%)."
        )

    if dump_pending > 5:
        notes.append(
            f"{dump_pending} dump batches are pending — Auto-Graphify worker "
            "may be lagging. Check celery-worker logs."
        )

    return notes


__all__ = ["build_hivemind_ingest_overview"]
