"""Shared context persistence bridge for supervisor + sub-agent steps."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from app.core.chroma_client import HIVE_MIND_COLLECTION, embed_and_store
from app.core.logging import get_logger
from app.core.neo4j_client import create_knowledge_node

logger = get_logger(__name__)


@dataclass(slots=True)
class SharedContextWriteResult:
    """Result of one shared-memory write operation."""

    vector_id: str | None
    graph_node_id: str | None


class SharedContextService:
    """Write/read façade for cross-agent shared memory updates."""

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
            ids = await embed_and_store(
                [text],
                collection_name=HIVE_MIND_COLLECTION,
                metadatas=[meta],
            )
            vector_id = ids[0] if ids else None
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

