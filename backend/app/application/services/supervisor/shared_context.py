"""Shared context persistence + retrieval contract bridge for supervisor runtime."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from dataclasses import dataclass
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chroma_client import HIVE_MIND_COLLECTION, embed_and_store, semantic_search
from app.core.config import settings
from app.core.logging import get_logger
from app.core.neo4j_client import create_knowledge_node, find_related
from app.infrastructure.persistence.models.supervisor_session import SupervisorSessionEvent
from app.infrastructure.persistence.models.task import Task

logger = get_logger(__name__)


@dataclass(slots=True)
class SharedContextWriteResult:
    """Result of one shared-memory write operation."""

    vector_id: str | None
    graph_node_id: str | None


@dataclass(slots=True)
class RetrievalBundle:
    """Resolved retrieval payload for one contract request."""

    contract: str
    sections: dict[str, Any]
    matched_sections: list[str]
    relevance_scores: dict[str, float] | None = None
    pruned_items: int = 0


class SharedContextService:
    """Write/read façade for cross-agent shared memory updates."""

    _KNOWN_RETRIEVAL_SECTIONS: tuple[str, ...] = (
        "customer_history",
        "customer_profile",
        "policy",
        "last_3_tasks",
        "last_7_days_tasks",
        "recent_events",
        "semantic_memory",
        "graph_context",
        "similar_past_decisions",
        "hybrid_memory",
    )
    _RETRIEVAL_ALIASES: dict[str, list[str]] = {
        "default_v2": [
            "last_7_days_tasks",
            "customer_profile",
            "similar_past_decisions",
            "hybrid_memory",
        ],
        "decision_support": [
            "policy",
            "similar_past_decisions",
            "customer_profile",
            "hybrid_memory",
        ],
        "triage": ["recent_events", "policy", "semantic_memory", "graph_context"],
    }
    _SECTION_SYNONYMS: dict[str, str] = {
        "customer": "customer_profile",
        "customer_context": "customer_profile",
        "similar_decisions": "similar_past_decisions",
        "last7_tasks": "last_7_days_tasks",
    }

    def parse_retrieval_contract(self, contract: str | None) -> list[str]:
        """Parse contract string into normalized known section ids."""

        raw = (contract or "").strip().lower()
        if not raw:
            return []
        candidates = [token.strip() for token in raw.replace("+", ",").split(",")]
        seen: set[str] = set()
        matched: list[str] = []
        known = set(self._KNOWN_RETRIEVAL_SECTIONS)
        for token in candidates:
            if not token:
                continue
            normalized = self._SECTION_SYNONYMS.get(token, token)
            if normalized in self._RETRIEVAL_ALIASES:
                for expanded in self._RETRIEVAL_ALIASES[normalized]:
                    if expanded in known and expanded not in seen:
                        seen.add(expanded)
                        matched.append(expanded)
                continue
            if normalized in known and normalized not in seen:
                seen.add(normalized)
                matched.append(normalized)
        return matched

    async def write_step_context(
        self,
        *,
        supervisor_session_id: uuid.UUID,
        sub_agent_session_id: uuid.UUID,
        role: str,
        goal: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> SharedContextWriteResult:
        """Store semantic memory + graph relation for one step output."""

        text = f"[{role}] goal={goal.strip()} :: {message.strip()}".strip()
        if not text:
            return SharedContextWriteResult(vector_id=None, graph_node_id=None)

        meta = {
            "kind": "supervisor_step",
            "role": role.strip().lower(),
            "supervisor_session_id": str(supervisor_session_id),
            "sub_agent_session_id": str(sub_agent_session_id),
            "payload": dict(payload or {}),
        }

        vector_id: str | None = None
        try:
            vector_id = await embed_and_store(
                text=text,
                metadata=meta,
                collection_name=HIVE_MIND_COLLECTION,
            )
        except Exception:
            logger.exception(
                "supervisor.shared_context.vector_write_failed",
                agent_id=str(sub_agent_session_id),
                swarm_id="",
                task_id=str(supervisor_session_id),
            )

        graph_node_id: str | None = None
        try:
            graph_node_id = await create_knowledge_node(
                content=text[:4000],
                source=f"supervisor:{supervisor_session_id}",
                confidence=0.7,
                topic_tags=[
                    "supervisor",
                    role.strip().lower() or "sub_agent",
                    "shared_context",
                ],
            )
        except Exception:
            logger.exception(
                "supervisor.shared_context.graph_write_failed",
                agent_id=str(sub_agent_session_id),
                swarm_id="",
                task_id=str(supervisor_session_id),
            )

        return SharedContextWriteResult(vector_id=vector_id, graph_node_id=graph_node_id)

    async def retrieve_context_bundle(
        self,
        db: AsyncSession,
        *,
        supervisor_session_id: uuid.UUID,
        query: str,
        contract: str | None,
    ) -> RetrievalBundle:
        """Resolve explicit retrieval contract sections into a compact context bundle."""

        matched = self.parse_retrieval_contract(contract)
        if not settings.retrieval_contract_enabled or not matched:
            return RetrievalBundle(contract=contract or "", sections={}, matched_sections=[])

        sections: dict[str, Any] = {}
        relevance_scores: dict[str, float] = {}
        pruned = 0
        base_query = query.strip() or "supervisor session context"
        relevance_limit = settings.retrieval_v2_max_items_per_section
        relevance_floor = settings.retrieval_v2_min_relevance_score

        if "last_3_tasks" in matched or "recent_events" in matched:
            stmt = (
                select(SupervisorSessionEvent)
                .where(SupervisorSessionEvent.supervisor_session_id == supervisor_session_id)
                .order_by(desc(SupervisorSessionEvent.occurred_at))
                .limit(3)
            )
            rows = list((await db.scalars(stmt)).all())
            compact_events = [
                {
                    "event_type": row.event_type,
                    "message": row.message[:500],
                    "occurred_at": row.occurred_at.isoformat(),
                }
                for row in rows
            ]
            if "last_3_tasks" in matched:
                sections["last_3_tasks"] = compact_events
            if "recent_events" in matched:
                sections["recent_events"] = compact_events

        if "last_7_days_tasks" in matched:
            since = datetime.now(tz=UTC) - timedelta(days=7)
            task_stmt = (
                select(Task)
                .where(Task.created_at >= since)
                .order_by(desc(Task.created_at))
                .limit(24)
            )
            task_rows = list((await db.scalars(task_stmt)).all())
            sections["last_7_days_tasks"] = [
                {
                    "id": str(row.id),
                    "title": row.title[:220],
                    "status": row.status.value,
                    "priority": row.priority,
                    "created_at": row.created_at.isoformat(),
                    "relevance_score": self._score_text_overlap(base_query, row.title),
                }
                for row in task_rows
            ][:relevance_limit]

        async def _fetch_semantic(probe: str, *, cap: int = 6) -> list[dict[str, Any]]:
            try:
                rows = await semantic_search(probe, HIVE_MIND_COLLECTION, n_results=cap)
            except Exception:
                logger.exception(
                    "supervisor.shared_context.retrieval_semantic_failed",
                    agent_id="shared_context",
                    swarm_id="",
                    task_id=str(supervisor_session_id),
                )
                return []
            parsed: list[dict[str, Any]] = []
            for item in rows:
                distance = item.get("distance")
                score = self._score_distance(distance)
                parsed.append(
                    {
                        "source_type": "vector",
                        "id": item.get("id"),
                        "document": str(item.get("document") or "")[:360],
                        "distance": distance,
                        "metadata": dict(item.get("metadata") or {}),
                        "relevance_score": score,
                    },
                )
            return parsed

        async def _fetch_graph(probe: str, *, cap: int = 6) -> list[dict[str, Any]]:
            try:
                rows = await find_related(probe, limit=cap)
            except Exception:
                logger.exception(
                    "supervisor.shared_context.retrieval_graph_failed",
                    agent_id="shared_context",
                    swarm_id="",
                    task_id=str(supervisor_session_id),
                )
                return []
            out: list[dict[str, Any]] = []
            for item in rows:
                confidence = item.get("confidence")
                score = self._score_confidence(confidence)
                out.append(
                    {
                        "source_type": "graph",
                        "id": item.get("id"),
                        "document": str(item.get("content") or "")[:360],
                        "metadata": {
                            "source": item.get("source"),
                            "topic_tags": item.get("topic_tags") or [],
                        },
                        "relevance_score": score,
                    },
                )
            return out

        if "customer_history" in matched:
            rows = await _fetch_semantic(f"{base_query} customer history", cap=8)
            kept, dropped = self.rank_and_prune(rows, limit=relevance_limit, min_score=relevance_floor)
            sections["customer_history"] = kept
            pruned += dropped
            relevance_scores["customer_history"] = self._section_score(kept)
        if "customer_profile" in matched:
            rows = await _fetch_semantic(f"{base_query} customer profile preferences", cap=8)
            kept, dropped = self.rank_and_prune(rows, limit=max(1, relevance_limit // 2), min_score=relevance_floor)
            profile = kept[0] if kept else None
            sections["customer_profile"] = profile or {}
            pruned += dropped
            relevance_scores["customer_profile"] = float(profile.get("relevance_score", 0.0)) if profile else 0.0
        if "policy" in matched:
            rows = await _fetch_semantic(f"{base_query} policy constraints", cap=6)
            kept, dropped = self.rank_and_prune(rows, limit=relevance_limit, min_score=relevance_floor)
            sections["policy"] = kept
            pruned += dropped
            relevance_scores["policy"] = self._section_score(kept)
        if "semantic_memory" in matched:
            rows = await _fetch_semantic(base_query, cap=10)
            kept, dropped = self.rank_and_prune(rows, limit=relevance_limit, min_score=relevance_floor)
            sections["semantic_memory"] = kept
            pruned += dropped
            relevance_scores["semantic_memory"] = self._section_score(kept)
        if "graph_context" in matched:
            rows = await _fetch_graph(base_query, cap=8)
            kept, dropped = self.rank_and_prune(rows, limit=relevance_limit, min_score=relevance_floor)
            sections["graph_context"] = kept
            pruned += dropped
            relevance_scores["graph_context"] = self._section_score(kept)
        if "similar_past_decisions" in matched or "hybrid_memory" in matched:
            vector_rows = await _fetch_semantic(f"{base_query} prior decision rationale", cap=10)
            graph_rows = await _fetch_graph(f"{base_query} decision", cap=8)
            hybrid_rows = self._merge_hybrid_rows(vector_rows, graph_rows)
            kept, dropped = self.rank_and_prune(hybrid_rows, limit=relevance_limit, min_score=relevance_floor)
            pruned += dropped
            if "similar_past_decisions" in matched:
                sections["similar_past_decisions"] = kept
                relevance_scores["similar_past_decisions"] = self._section_score(kept)
            if "hybrid_memory" in matched:
                sections["hybrid_memory"] = kept
                relevance_scores["hybrid_memory"] = self._section_score(kept)

        return RetrievalBundle(
            contract=contract or "",
            sections=sections,
            matched_sections=matched,
            relevance_scores=relevance_scores,
            pruned_items=pruned,
        )

    @staticmethod
    def render_bundle_for_prompt(bundle: RetrievalBundle) -> str:
        """Render retrieval bundle into a short deterministic prompt appendix."""

        if not bundle.matched_sections:
            return ""
        lines: list[str] = [f"Retrieval contract: {bundle.contract or '(none)'}"]
        for key in bundle.matched_sections:
            value = bundle.sections.get(key)
            score = float((bundle.relevance_scores or {}).get(key, 0.0))
            if isinstance(value, list):
                lines.append(f"- {key}: {len(value)} rows (score={score:.2f})")
            elif isinstance(value, dict):
                lines.append(f"- {key}: {len(value.keys())} fields (score={score:.2f})")
            elif value is None:
                lines.append(f"- {key}: empty")
            else:
                lines.append(f"- {key}: loaded")
        if bundle.pruned_items:
            lines.append(f"- auto_pruned_items: {bundle.pruned_items}")
        return "\n".join(lines)

    @staticmethod
    def rank_and_prune(
        rows: list[dict[str, Any]],
        *,
        limit: int,
        min_score: float,
    ) -> tuple[list[dict[str, Any]], int]:
        """Sort rows by relevance score and prune weak context."""

        ranked = sorted(
            rows,
            key=lambda item: float(item.get("relevance_score") or 0.0),
            reverse=True,
        )
        filtered = [item for item in ranked if float(item.get("relevance_score") or 0.0) >= min_score]
        kept = filtered[: max(1, int(limit))]
        dropped = max(0, len(rows) - len(kept))
        return kept, dropped

    @staticmethod
    def _score_distance(raw: Any) -> float:
        try:
            distance = float(raw)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, 1.0 - distance))

    @staticmethod
    def _score_confidence(raw: Any) -> float:
        try:
            confidence = float(raw)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, confidence))

    @staticmethod
    def _score_text_overlap(query: str, text: str) -> float:
        q_tokens = {item.lower() for item in query.split() if item.strip()}
        t_tokens = {item.lower() for item in text.split() if item.strip()}
        if not q_tokens or not t_tokens:
            return 0.0
        overlap = len(q_tokens.intersection(t_tokens))
        return max(0.0, min(1.0, overlap / max(1, len(q_tokens))))

    @staticmethod
    def _merge_hybrid_rows(
        vector_rows: list[dict[str, Any]],
        graph_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for row in [*vector_rows, *graph_rows]:
            key = str(row.get("id") or row.get("document") or "")
            if not key:
                continue
            old = out.get(key)
            if old is None:
                out[key] = row
                continue
            out[key] = {
                **old,
                "relevance_score": max(
                    float(old.get("relevance_score") or 0.0),
                    float(row.get("relevance_score") or 0.0),
                ),
                "source_type": "hybrid",
            }
        return list(out.values())

    @staticmethod
    def _section_score(rows: list[dict[str, Any]]) -> float:
        if not rows:
            return 0.0
        values = [float(item.get("relevance_score") or 0.0) for item in rows]
        return round(sum(values) / max(1, len(values)), 4)

