"""Shared context persistence + retrieval contract bridge for supervisor runtime."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chroma_client import HIVE_MIND_COLLECTION, embed_and_store, semantic_search
from app.core.config import settings
from app.core.logging import get_logger
from app.core.neo4j_client import create_knowledge_node, find_related
from app.infrastructure.persistence.models.supervisor_session import SupervisorSessionEvent

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


class SharedContextService:
    """Write/read façade for cross-agent shared memory updates."""

    _KNOWN_RETRIEVAL_SECTIONS: tuple[str, ...] = (
        "customer_history",
        "policy",
        "last_3_tasks",
        "recent_events",
        "semantic_memory",
        "graph_context",
    )

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
            if token in known and token not in seen:
                seen.add(token)
                matched.append(token)
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
        base_query = query.strip() or "supervisor session context"

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

        async def _fetch_semantic(probe: str, *, cap: int = 4) -> list[dict[str, Any]]:
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
            return [
                {
                    "id": item.get("id"),
                    "document": str(item.get("document") or "")[:360],
                    "distance": item.get("distance"),
                    "metadata": dict(item.get("metadata") or {}),
                }
                for item in rows
            ]

        if "customer_history" in matched:
            sections["customer_history"] = await _fetch_semantic(f"{base_query} customer history", cap=5)
        if "policy" in matched:
            sections["policy"] = await _fetch_semantic(f"{base_query} policy constraints", cap=4)
        if "semantic_memory" in matched:
            sections["semantic_memory"] = await _fetch_semantic(base_query, cap=6)
        if "graph_context" in matched:
            try:
                sections["graph_context"] = await find_related(base_query, limit=5)
            except Exception:
                logger.exception(
                    "supervisor.shared_context.retrieval_graph_failed",
                    agent_id="shared_context",
                    swarm_id="",
                    task_id=str(supervisor_session_id),
                )
                sections["graph_context"] = []

        return RetrievalBundle(contract=contract or "", sections=sections, matched_sections=matched)

    @staticmethod
    def render_bundle_for_prompt(bundle: RetrievalBundle) -> str:
        """Render retrieval bundle into a short deterministic prompt appendix."""

        if not bundle.matched_sections:
            return ""
        lines: list[str] = [f"Retrieval contract: {bundle.contract or '(none)'}"]
        for key in bundle.matched_sections:
            value = bundle.sections.get(key)
            if isinstance(value, list):
                lines.append(f"- {key}: {len(value)} rows")
            elif isinstance(value, dict):
                lines.append(f"- {key}: {len(value.keys())} fields")
            elif value is None:
                lines.append(f"- {key}: empty")
            else:
                lines.append(f"- {key}: loaded")
        return "\n".join(lines)

