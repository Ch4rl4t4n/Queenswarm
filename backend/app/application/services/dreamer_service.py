"""Nightly dreaming loop service for knowledge consolidation."""

from __future__ import annotations

import traceback
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from prometheus_client import Counter
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_client import publish_event
from app.domain.dreaming.models import DreamCycle, DreamCycleStatus
from app.infrastructure.persistence.models.dream_cycle import DreamCycleORM, DreamCycleStatusORM, DreamInsightORM
from app.infrastructure.persistence.models.knowledge import KnowledgeItem
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession, SupervisorSessionEvent

logger = get_logger(__name__)

DREAM_CYCLE_FAILURES_TOTAL = Counter(
    "queenswarm_dream_cycle_failures_total",
    "Count of failed nightly dream cycles.",
)


class SupportsLiteSummary(Protocol):
    """Protocol for LLM routers used by DreamerService."""

    async def summarize(self, items: list[str]) -> str:  # pragma: no cover - optional capability
        """Return one-paragraph summary."""


@dataclass(slots=True)
class _RawLearningItem:
    source_kind: str
    source_ref: str
    text: str
    metadata: dict[str, Any]


class DreamerService:
    """Consolidates recent knowledge into de-duplicated insight artifacts."""

    def __init__(
        self,
        *,
        postgres_session_factory: async_sessionmaker[AsyncSession],
        chroma_client: Any,
        neo4j_driver: Any,
        litellm_router: Any,
        logger_instance: Any | None = None,
    ) -> None:
        self._session_factory = postgres_session_factory
        self._chroma = chroma_client
        self._neo4j = neo4j_driver
        self._litellm_router = litellm_router
        self._logger = logger_instance or logger

    async def run_cycle(self, *, tenant_id: uuid.UUID, window_hours: int = 24) -> DreamCycle:
        """Run one full dream cycle and return the resulting domain object."""

        async with self._session_factory() as session:
            cycle = DreamCycleORM(
                tenant_id=tenant_id,
                status=DreamCycleStatusORM.RUNNING,
                started_at=datetime.now(tz=UTC),
                items_processed=0,
                items_deduplicated=0,
                items_consolidated=0,
                digest_md="",
                dream_report={},
            )
            session.add(cycle)
            await session.flush()
            try:
                insights_count = await self._execute_cycle_body(
                    session=session,
                    cycle=cycle,
                    tenant_id=tenant_id,
                    window_hours=window_hours,
                )
                cycle.status = DreamCycleStatusORM.COMPLETED
                cycle.finished_at = datetime.now(tz=UTC)
                await session.commit()
                self._logger.info(
                    "dreamer.cycle.completed",
                    agent_id="dreamer_service",
                    swarm_id="nightly_dreaming",
                    task_id=str(cycle.id),
                    insights_count=insights_count,
                )
            except Exception as exc:
                cycle.status = DreamCycleStatusORM.FAILED
                cycle.finished_at = datetime.now(tz=UTC)
                cycle.traceback_text = traceback.format_exc()
                await session.commit()
                DREAM_CYCLE_FAILURES_TOTAL.inc()
                self._logger.exception(
                    "dreamer.cycle.failed",
                    agent_id="dreamer_service",
                    swarm_id="nightly_dreaming",
                    task_id=str(cycle.id),
                    error_type=type(exc).__name__,
                )
                raise
            return self._to_domain(cycle)

    async def get_last_digest(self, *, tenant_id: uuid.UUID) -> str | None:
        """Return markdown digest from latest completed dream cycle."""

        async with self._session_factory() as session:
            row = await session.scalar(
                select(DreamCycleORM)
                .where(
                    DreamCycleORM.status == DreamCycleStatusORM.COMPLETED,
                    DreamCycleORM.tenant_id == tenant_id,
                )
                .order_by(DreamCycleORM.started_at.desc())
                .limit(1)
            )
            if row is None:
                return None
            return row.digest_md or None

    async def _execute_cycle_body(
        self,
        *,
        session: AsyncSession,
        cycle: DreamCycleORM,
        tenant_id: uuid.UUID,
        window_hours: int,
    ) -> int:
        window_start = datetime.now(tz=UTC) - timedelta(hours=max(1, int(window_hours)))
        items = await self._fetch_recent_items(session=session, tenant_id=tenant_id, window_start=window_start)
        cycle.items_processed = len(items)
        grouped = self._cluster_items(items)
        cycle.items_deduplicated = sum(max(0, len(cluster) - 1) for cluster in grouped)

        consolidated: list[DreamInsightORM] = []
        decay_deleted = 0
        for cluster in grouped:
            if len(cluster) < 2:
                continue
            summary = await self._summarize_cluster(cluster)
            confidence = min(0.95, 0.65 + (len(cluster) * 0.05))
            neo4j_node_id = await self._upsert_neo4j_insight(summary=summary, confidence=confidence)
            chroma_doc_id = await self._upsert_chroma_insight(
                cycle_id=cycle.id,
                summary=summary,
                confidence=confidence,
                cluster=cluster,
            )
            insight = DreamInsightORM(
                cycle_id=cycle.id,
                tenant_id=tenant_id,
                source_kind=cluster[0].source_kind,
                source_ref=cluster[0].source_ref,
                summary=summary,
                confidence=confidence,
                neo4j_node_id=neo4j_node_id,
                chroma_doc_id=chroma_doc_id,
            )
            session.add(insight)
            consolidated.append(insight)

        decay_deleted = await self._apply_memory_decay()
        cycle.items_consolidated = len(consolidated)
        cycle.dream_report = self._build_dream_report(items=items, consolidated=consolidated)
        cycle.digest_md = self._build_digest(
            consolidated=consolidated,
            processed=cycle.items_processed,
            deduplicated=cycle.items_deduplicated,
            decay_deleted=decay_deleted,
        )
        await self._persist_hivemind_knowledge_report(
            session=session,
            tenant_id=tenant_id,
            cycle=cycle,
            consolidated=consolidated,
        )
        await publish_event(
            "dream:digest",
            {
                "cycle_id": str(cycle.id),
                "tenant_id": str(tenant_id),
                "status": "completed",
                "digest_md": cycle.digest_md,
                "items_consolidated": cycle.items_consolidated,
            },
        )
        return len(consolidated)

    async def _fetch_recent_items(
        self,
        *,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        window_start: datetime,
    ) -> list[_RawLearningItem]:
        rows: list[_RawLearningItem] = []

        task_rows = await session.execute(
            text(
                """
                SELECT id::text AS source_ref, COALESCE(title, '') AS txt
                FROM tasks
                WHERE tenant_id = :tenant_id
                  AND status = 'completed'
                  AND completed_at IS NOT NULL
                  AND completed_at >= :window_start
                ORDER BY completed_at DESC
                LIMIT 250
                """,
            ),
            {"window_start": window_start, "tenant_id": tenant_id},
        )
        for raw in task_rows:
            txt = str(raw.txt or "").strip()
            if txt:
                rows.append(
                    _RawLearningItem(
                        source_kind="task_ledger",
                        source_ref=str(raw.source_ref),
                        text=txt,
                        metadata={"signal": "success"},
                    ),
                )

        external_rows = await session.execute(
            text(
                """
                SELECT id::text AS source_ref, COALESCE(text_report, '') AS txt
                FROM external_outputs
                WHERE tenant_id = :tenant_id
                  AND created_at >= :window_start
                ORDER BY created_at DESC
                LIMIT 250
                """,
            ),
            {"window_start": window_start, "tenant_id": tenant_id},
        )
        for raw in external_rows:
            txt = str(raw.txt or "").strip()
            if txt:
                rows.append(
                    _RawLearningItem(
                        source_kind="forager_output",
                        source_ref=str(raw.source_ref),
                        text=txt,
                        metadata={"signal": "observation"},
                    ),
                )

        relay_rows = await session.execute(
            text(
                """
                SELECT id::text AS source_ref, COALESCE(insight_text, '') AS txt
                FROM learning_logs
                WHERE tenant_id = :tenant_id
                  AND created_at >= :window_start
                ORDER BY created_at DESC
                LIMIT 250
                """,
            ),
            {"window_start": window_start, "tenant_id": tenant_id},
        )
        for raw in relay_rows:
            txt = str(raw.txt or "").strip()
            if txt:
                rows.append(
                    _RawLearningItem(
                        source_kind="waggle_relay",
                        source_ref=str(raw.source_ref),
                        text=txt,
                        metadata={"signal": "lesson"},
                    ),
                )

        sessions = list(
            (
                await session.scalars(
                    select(SupervisorSession)
                    .where(
                        SupervisorSession.tenant_id == tenant_id,
                        SupervisorSession.created_at >= window_start,
                    )
                    .order_by(SupervisorSession.created_at.desc())
                    .limit(int(settings.dreaming_session_limit)),
                )
            ).all(),
        )
        for row in sessions:
            status_tag = str(row.status or "").strip().lower()
            summary_blob = str((row.context_summary or {}).get("summary") or "").strip()
            text_blob = f"goal={row.goal.strip()} status={status_tag} {summary_blob}".strip()
            if text_blob:
                rows.append(
                    _RawLearningItem(
                        source_kind="supervisor_session",
                        source_ref=str(row.id),
                        text=text_blob,
                        metadata={"signal": "error" if status_tag in {"failed", "needs_input"} else "success"},
                    ),
                )

        events = list(
            (
                await session.scalars(
                    select(SupervisorSessionEvent)
                    .where(
                        SupervisorSessionEvent.tenant_id == tenant_id,
                        SupervisorSessionEvent.created_at >= window_start,
                    )
                    .order_by(SupervisorSessionEvent.created_at.desc())
                    .limit(int(settings.dreaming_event_limit)),
                )
            ).all(),
        )
        for row in events:
            msg = str(row.message or "").strip()
            if not msg:
                continue
            level = str(row.level or "info").lower()
            rows.append(
                _RawLearningItem(
                    source_kind="supervisor_event",
                    source_ref=str(row.id),
                    text=f"{row.event_type}: {msg}",
                    metadata={"signal": "error" if level in {"error", "warning"} else "observation"},
                ),
            )

        return rows

    def _cluster_items(self, items: list[_RawLearningItem]) -> list[list[_RawLearningItem]]:
        if not items:
            return []
        groups: dict[str, list[_RawLearningItem]] = {}
        for item in items:
            key = self._topic_key(item.text)
            groups.setdefault(key, []).append(item)
        return list(groups.values())

    def _topic_key(self, text_blob: str) -> str:
        words = [w.strip(".,:;!?()[]{}\"'").lower() for w in text_blob.split()]
        tokens = [w for w in words if len(w) > 3]
        if len(tokens) < 2:
            return "misc"
        return "|".join(tokens[:4])

    async def _summarize_cluster(self, cluster: list[_RawLearningItem]) -> str:
        payload = [item.text for item in cluster]
        router = self._litellm_router
        if hasattr(router, "summarize"):
            maybe = await router.summarize(payload)
            cleaned = str(maybe or "").strip()
            if cleaned:
                return cleaned
        lead = payload[0][:220]
        return f"Consolidated recurring signal: {lead}"

    async def _upsert_neo4j_insight(self, *, summary: str, confidence: float) -> str | None:
        try:
            node_id = str(uuid.uuid4())
            async with self._neo4j.session(database="neo4j") as session:
                await session.run(
                    """
                    MERGE (i:Insight {id: $id})
                    SET i.summary = $summary,
                        i.confidence = $confidence,
                        i.created_at = datetime()
                    """,
                    id=node_id,
                    summary=summary,
                    confidence=float(confidence),
                )
            return node_id
        except Exception as exc:  # noqa: BLE001
            self._logger.warning(
                "dreamer.neo4j.write_failed",
                agent_id="dreamer_service",
                swarm_id="nightly_dreaming",
                task_id="",
                error=str(exc),
            )
            return None

    async def _upsert_chroma_insight(
        self,
        *,
        cycle_id: uuid.UUID,
        summary: str,
        confidence: float,
        cluster: list[_RawLearningItem],
    ) -> str | None:
        doc_id = str(uuid.uuid4())
        metadata = {
            "cycle_id": str(cycle_id),
            "confidence": float(confidence),
            "source_kind": cluster[0].source_kind,
            "source_refs": [entry.source_ref for entry in cluster[:8]],
        }
        chroma = self._chroma
        if hasattr(chroma, "add"):
            await chroma.add(
                collection="consolidated_insights",
                ids=[doc_id],
                documents=[summary],
                metadatas=[metadata],
            )
            return doc_id
        if hasattr(chroma, "upsert"):
            await chroma.upsert(
                collection="consolidated_insights",
                ids=[doc_id],
                documents=[summary],
                metadatas=[metadata],
            )
            return doc_id
        return None

    async def _apply_memory_decay(self) -> int:
        deleted = 0
        try:
            async with self._neo4j.session(database="neo4j") as session:
                await session.run(
                    """
                    MATCH (i:Insight)
                    WHERE i.created_at < datetime() - duration({days: $days})
                    SET i.confidence = coalesce(i.confidence, 1.0) * 0.9
                    """,
                    days=int(settings.memory_decay_days),
                )
                result = await session.run(
                    """
                    MATCH (i:Insight)
                    WHERE coalesce(i.confidence, 1.0) < 0.1
                    WITH collect(i) AS doomed
                    FOREACH (node IN doomed | DETACH DELETE node)
                    RETURN size(doomed) AS deleted_count
                    """,
                )
                row = await result.single()
                deleted = int(row["deleted_count"]) if row is not None else 0
        except Exception as exc:  # noqa: BLE001
            self._logger.warning(
                "dreamer.decay.failed",
                agent_id="dreamer_service",
                swarm_id="nightly_dreaming",
                task_id="",
                error=str(exc),
            )
        return deleted

    def _build_digest(
        self,
        *,
        consolidated: list[DreamInsightORM],
        processed: int,
        deduplicated: int,
        decay_deleted: int,
    ) -> str:
        lines = [
            "# Nightly Dream Digest",
            "",
            f"- Processed items: {processed}",
            f"- Deduplicated items: {deduplicated}",
            f"- Consolidated insights: {len(consolidated)}",
            f"- Decayed/deleted stale insights: {decay_deleted}",
            "",
            "## Top Insights",
        ]
        for idx, item in enumerate(consolidated[:10], start=1):
            lines.append(f"{idx}. {item.summary[:320]}")
        if not consolidated:
            lines.append("No repetitive signals found in this window.")
        return "\n".join(lines)

    async def _persist_hivemind_knowledge_report(
        self,
        *,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        cycle: DreamCycleORM,
        consolidated: list[DreamInsightORM],
    ) -> None:
        """Upsert Dream Report into tenant KnowledgeItem space."""

        top_lines = [item.summary for item in consolidated[:6]]
        payload = cycle.dream_report if isinstance(cycle.dream_report, dict) else {}
        report_text = "\n".join(
            [
                f"Dream cycle {cycle.id}",
                f"Tenant: {tenant_id}",
                f"Processed={cycle.items_processed} Deduplicated={cycle.items_deduplicated} Consolidated={cycle.items_consolidated}",
                f"Success strategies: {', '.join(payload.get('success_strategies', [])[:3]) if isinstance(payload.get('success_strategies'), list) else 'n/a'}",
                f"Repeated errors: {', '.join(payload.get('repeated_errors', [])[:3]) if isinstance(payload.get('repeated_errors'), list) else 'n/a'}",
                "Top insights:",
                *[f"- {line}" for line in top_lines],
            ],
        )
        source_url = f"dream://tenant/{tenant_id}/cycle/{cycle.id}"
        existing = await session.scalar(
            select(KnowledgeItem).where(
                KnowledgeItem.tenant_id == tenant_id,
                KnowledgeItem.source_type == "dream_report",
                KnowledgeItem.source_url == source_url,
            ),
        )
        tags = ["dreaming", "memory-consolidation", "lessons-learned"]
        if existing is None:
            session.add(
                KnowledgeItem(
                    tenant_id=tenant_id,
                    source_url=source_url,
                    source_type="dream_report",
                    content_text=report_text[:20_000],
                    confidence_score=0.82,
                    topic_tags=tags,
                    decay_factor=1.0,
                    scraped_at=datetime.now(tz=UTC),
                ),
            )
            return
        existing.content_text = report_text[:20_000]
        existing.topic_tags = tags
        existing.scraped_at = datetime.now(tz=UTC)
        existing.confidence_score = 0.82

    def _build_dream_report(
        self,
        *,
        items: list[_RawLearningItem],
        consolidated: list[DreamInsightORM],
    ) -> dict[str, Any]:
        """Build concise machine-readable dream report."""

        successes: list[str] = []
        repeated_errors: list[str] = []
        improvement_ideas: list[str] = []
        seen_success: set[str] = set()
        seen_error: set[str] = set()
        for row in items:
            signal = str(row.metadata.get("signal") or "")
            compact = row.text.strip().replace("\n", " ")
            compact = compact[:180]
            if signal == "success":
                if compact and compact not in seen_success:
                    successes.append(compact)
                    seen_success.add(compact)
            elif signal == "error":
                if compact and compact not in seen_error:
                    repeated_errors.append(compact)
                    seen_error.add(compact)
        for insight in consolidated[:6]:
            line = str(insight.summary or "").strip()[:180]
            if line:
                improvement_ideas.append(line)
        return {
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "success_strategies": successes[:8],
            "repeated_errors": repeated_errors[:8],
            "improvement_proposals": improvement_ideas[:8],
            "summary": (
                f"Learned {len(successes[:8])} successful patterns, "
                f"detected {len(repeated_errors[:8])} repeated issues, "
                f"and consolidated {len(consolidated)} insights."
            ),
        }

    def _to_domain(self, cycle: DreamCycleORM) -> DreamCycle:
        status = DreamCycleStatus(cycle.status.value)
        return DreamCycle(
            id=cycle.id,
            tenant_id=cycle.tenant_id,
            started_at=cycle.started_at,
            finished_at=cycle.finished_at,
            items_processed=int(cycle.items_processed),
            items_deduplicated=int(cycle.items_deduplicated),
            items_consolidated=int(cycle.items_consolidated),
            digest_md=cycle.digest_md,
            dream_report=dict(cycle.dream_report or {}),
            status=status,
        )


__all__ = ["DreamerService"]
