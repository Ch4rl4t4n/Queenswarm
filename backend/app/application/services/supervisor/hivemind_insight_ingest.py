"""Persist supervisor LLM outputs as tagged HiveMind VaultDocuments."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.auto_graphify_service import _extract_tags
from app.core.chroma_client import HIVE_MIND_COLLECTION, embed_and_store
from app.core.config import settings
from app.core.logging import get_logger
from app.domain.hive_mind.graph import persist_graphify_ingest_bundle
from app.infrastructure.persistence.models.knowledge import KnowledgeItem

logger = get_logger(__name__)

_HIVEMIND_TAG = "hivemind-candidate"
_INSIGHT_TITLE_RE = re.compile(r"\[INSIGHT\][^\n]{0,120}", re.IGNORECASE)


def extract_insight_markdown_blocks(text: str) -> list[dict[str, Any]]:
    """Parse LLM markdown for ``[INSIGHT]`` pages to graphify."""

    cleaned = text.strip()
    if not cleaned:
        return []

    blocks: list[dict[str, Any]] = []
    sections = re.split(r"(?=\n##\s+HiveMind write-back|\n#\s+\[INSIGHT\])", cleaned, flags=re.IGNORECASE)
    for section in sections:
        chunk = section.strip()
        if not chunk:
            continue
        if "[insight]" not in chunk.lower() and "hivemind write-back" not in chunk.lower():
            continue
        title_match = _INSIGHT_TITLE_RE.search(chunk)
        title = title_match.group(0).strip() if title_match else "[INSIGHT] Supervisor capture"
        if _HIVEMIND_TAG not in chunk:
            chunk = f"# {_HIVEMIND_TAG}\n\n{chunk}"
        blocks.append({"title": title[:240], "body": chunk[:120_000]})

    if not blocks and _HIVEMIND_TAG in cleaned.lower() and len(cleaned) >= 80:
        title = "[INSIGHT] Supervisor session capture"
        first_line = cleaned.splitlines()[0].strip("# ").strip()[:120]
        if first_line:
            title = first_line if first_line.lower().startswith("[insight]") else f"[INSIGHT] {first_line}"
        blocks.append({"title": title[:240], "body": cleaned[:120_000]})

    return blocks[:4]


async def ingest_supervisor_insights(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    supervisor_session_id: uuid.UUID,
    sub_agent_role: str,
    llm_output: str,
) -> list[str]:
    """Write parsed insights to vault mirror, Neo4j, vectors, and KnowledgeItem."""

    if not settings.hive_mind_enabled:
        return []

    docs = extract_insight_markdown_blocks(llm_output)
    if not docs:
        return []

    batch_id = uuid.uuid4()
    graph_files: list[dict[str, Any]] = []
    ingested_ids: list[str] = []

    vault_root = Path(settings.hive_mind_vault_root).expanduser()
    rel_folder = f"supervisor/{tenant_id}/{supervisor_session_id}"
    vault_dir = vault_root / rel_folder
    vault_dir.mkdir(parents=True, exist_ok=True)

    for idx, doc in enumerate(docs):
        body = str(doc.get("body") or "").strip()
        title = str(doc.get("title") or "[INSIGHT] capture").strip()
        if len(body) < 40:
            continue
        rel_path = f"{rel_folder}/insight-{sub_agent_role}-{idx + 1}.md"
        doc_id = hashlib.sha256(f"{tenant_id}:{supervisor_session_id}:{rel_path}".encode()).hexdigest()
        dest = vault_root / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body, encoding="utf-8")
        tags = _extract_tags(rel_path=rel_path, text=body)
        if _HIVEMIND_TAG not in tags:
            tags.insert(0, _HIVEMIND_TAG)
        tags.append(f"role:{sub_agent_role}")

        if settings.hive_mind_chroma_enabled:
            try:
                await embed_and_store(
                    f"# {title}\npath:{rel_path}\n\n{body}",
                    {
                        "source": "supervisor_llm",
                        "tenant_id": str(tenant_id),
                        "supervisor_session_id": str(supervisor_session_id),
                        "role": sub_agent_role,
                        "doc_id": doc_id[:24],
                    },
                    HIVE_MIND_COLLECTION,
                )
            except (RuntimeError, ValueError, TypeError) as exc:
                logger.warning(
                    "supervisor_insight.embed_failed",
                    agent_id=sub_agent_role,
                    swarm_id=str(supervisor_session_id),
                    task_id=doc_id[:24],
                    error=str(exc),
                )

        db.add(
            KnowledgeItem(
                tenant_id=tenant_id,
                source_url=f"supervisor://{supervisor_session_id}/{sub_agent_role}/{idx + 1}",
                source_type="supervisor_llm",
                content_text=body,
                confidence_score=0.72,
                topic_tags=tags[:16],
                decay_factor=1.0,
                scraped_at=datetime.now(tz=UTC),
                neo4j_node_id=doc_id,
            ),
        )
        graph_files.append(
            {
                "doc_id": doc_id,
                "rel_path": rel_path,
                "title": title,
                "excerpt": body[:2400],
                "tags": tags[:16],
            },
        )
        ingested_ids.append(doc_id)

    if graph_files:
        try:
            await persist_graphify_ingest_bundle(
                tenant_id=tenant_id,
                batch_id=batch_id,
                folder_label=f"supervisor-{sub_agent_role}",
                files=graph_files,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "supervisor_insight.graph_failed",
                agent_id=sub_agent_role,
                swarm_id=str(supervisor_session_id),
                error=str(exc),
            )

    await db.flush()
    return ingested_ids


__all__ = ["extract_insight_markdown_blocks", "ingest_supervisor_insights"]
