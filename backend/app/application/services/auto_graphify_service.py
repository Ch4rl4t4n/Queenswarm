"""Auto-Graphify — folder upload → vault mirror + Neo4j graph + vector embed."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import aiofiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.hive_tier import FIXED_ORCHESTRATOR_AGENT_NAME
from app.application.services.verified_pollen_leaderboard import record_verified_pollen_reward
from app.core.chroma_client import HIVE_MIND_COLLECTION, embed_and_store
from app.core.config import settings
from app.core.logging import get_logger
from app.domain.hive_mind.graph import persist_graphify_ingest_bundle
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.graphify_batch import GraphifyBatchORM, GraphifyStatusORM
from app.infrastructure.persistence.models.knowledge import KnowledgeItem, LearningLog
from app.infrastructure.persistence.models.reward import PollenReward

logger = get_logger(__name__)

_TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".json", ".csv", ".py", ".html", ".xml", ".yaml", ".yml", ".log"}
_TAG_RE = re.compile(r"#([a-zA-Z][\w-]{1,48})")


def graphify_upload_dir(*, tenant_id: uuid.UUID, batch_id: uuid.UUID) -> Path:
    """Return tenant-scoped staging directory for one graphify batch."""

    root = Path(settings.auto_graphify_upload_root).expanduser().resolve()
    return root / str(tenant_id) / str(batch_id)


def graphify_vault_dir(*, tenant_id: uuid.UUID, batch_id: uuid.UUID, folder_label: str) -> Path:
    """Return Obsidian-compatible vault destination for processed batch."""

    root = Path(settings.hive_mind_vault_root).expanduser().resolve()
    slug = re.sub(r"[^a-z0-9]+", "-", (folder_label or "graphify").lower()).strip("-")[:48] or "graphify"
    return root / "graphify" / str(tenant_id) / f"{batch_id.hex[:8]}_{slug}"


def _read_text_file(path: Path) -> str | None:
    """Read UTF-8 text from supported ingest files."""

    if path.suffix.lower() not in _TEXT_SUFFIXES:
        return None
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    text = raw.strip()
    return text if text else None


def _extract_tags(*, rel_path: str, text: str) -> list[str]:
    """Derive topic tags from path segments and markdown hashtags."""

    tags: list[str] = []
    for part in Path(rel_path).parts[:-1]:
        norm = part.strip().lower().replace(" ", "_")
        if len(norm) >= 2 and norm not in tags:
            tags.append(norm[:64])
    for match in _TAG_RE.findall(text):
        norm = match.strip().lower().replace(" ", "_")
        if norm and norm not in tags:
            tags.append(norm[:64])
    tags.append("auto_graphify")
    return tags[:16]


def _build_summary_md(
    *,
    folder_label: str,
    file_count: int,
    items_ingested: int,
    graph_nodes_created: int,
    vectors_embedded: int,
    pollen_earned: float,
    vault_rel_path: str | None,
) -> str:
    """Compose verified graphify summary markdown."""

    lines = [
        "# Auto-Graphify ingest report",
        "",
        f"- Folder: **{folder_label or 'upload'}**",
        f"- Files received: **{file_count}**",
        f"- Documents ingested: **{items_ingested}**",
        f"- Graph nodes created: **{graph_nodes_created}**",
        f"- Vector chunks embedded: **{vectors_embedded}**",
        f"- Pollen earned: **{pollen_earned:.1f}**",
        "",
        "## Next steps",
    ]
    if items_ingested == 0:
        lines.append("- No readable text files found — add `.md` or `.txt` notes.")
    else:
        lines.append("- Open HiveMind graph to explore new vault documents.")
        lines.append("- Use selective recall in supervisor sessions for token savings.")
    if vault_rel_path:
        lines.append(f"- Vault mirror: `{vault_rel_path}`")
    return "\n".join(lines).strip() + "\n"


async def _resolve_orchestrator_agent(session: AsyncSession, *, tenant_id: uuid.UUID) -> Agent | None:
    """Find tenant orchestrator bee for pollen credit."""

    orch = await session.scalar(
        select(Agent).where(Agent.name == FIXED_ORCHESTRATOR_AGENT_NAME).limit(1),
    )
    if orch is not None:
        return orch
    _ = tenant_id
    rows = list(
        (
            await session.scalars(
                select(Agent).order_by(Agent.created_at.asc()).limit(40),
            )
        ).all(),
    )
    return rows[0] if rows else None


async def _grant_graphify_pollen(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    amount: float,
    batch_id: uuid.UUID,
) -> float:
    """Credit verified pollen after graphify ingest."""

    if amount <= 0.0:
        return 0.0
    agent = await _resolve_orchestrator_agent(session, tenant_id=tenant_id)
    if agent is None:
        logger.warning("auto_graphify.pollen_skipped_no_agent", tenant_id=str(tenant_id), batch_id=str(batch_id))
        return 0.0
    stamp = datetime.now(tz=UTC)
    session.add(
        PollenReward(
            agent_id=agent.id,
            task_id=None,
            amount=float(amount),
            reason="Verified Auto-Graphify folder ingest.",
            verified_reward=True,
        ),
    )
    agent.pollen_points = float(agent.pollen_points) + float(amount)
    session.add(
        LearningLog(
            agent_id=agent.id,
            task_id=None,
            insight_text=f"Auto-Graphify batch {batch_id} mirrored to vault + graph.",
            applied_at=stamp,
            pollen_earned=float(amount),
            tenant_id=tenant_id,
        ),
    )
    await session.flush()
    if agent.swarm_id is not None:
        await record_verified_pollen_reward(
            agent_id=agent.id,
            swarm_id=agent.swarm_id,
            amount=float(amount),
            task_id=None,
        )
    return float(amount)


class AutoGraphifyService:
    """Queue and process folder uploads into Hive Mind graph + vault."""

    def __init__(self, *, db: AsyncSession) -> None:
        self._db = db

    async def get_batch(self, *, tenant_id: uuid.UUID, batch_id: uuid.UUID) -> GraphifyBatchORM | None:
        """Load one tenant-scoped batch."""

        return await self._db.scalar(
            select(GraphifyBatchORM).where(
                GraphifyBatchORM.id == batch_id,
                GraphifyBatchORM.tenant_id == tenant_id,
            ),
        )

    async def latest_summary(
        self,
        *,
        tenant_id: uuid.UUID,
        window_hours: int = 168,
    ) -> GraphifyBatchORM | None:
        """Return newest completed batch inside reporting window."""

        since = datetime.now(tz=UTC) - timedelta(hours=max(1, window_hours))
        return await self._db.scalar(
            select(GraphifyBatchORM)
            .where(
                GraphifyBatchORM.tenant_id == tenant_id,
                GraphifyBatchORM.status == GraphifyStatusORM.COMPLETED,
                GraphifyBatchORM.created_at >= since,
            )
            .order_by(GraphifyBatchORM.created_at.desc())
            .limit(1),
        )

    async def process_batch(
        self,
        *,
        tenant_id: uuid.UUID,
        batch_id: uuid.UUID,
    ) -> GraphifyBatchORM:
        """Mirror files to vault, persist graph nodes, embed vectors, award pollen."""

        batch = await self.get_batch(tenant_id=tenant_id, batch_id=batch_id)
        if batch is None:
            raise ValueError(f"Graphify batch not found: {batch_id}")
        batch.status = GraphifyStatusORM.PROCESSING
        batch.error_text = None
        await self._db.flush()

        log = logger.bind(agent_id="auto_graphify", swarm_id=str(tenant_id), task_id=str(batch_id))
        staging_dir = graphify_upload_dir(tenant_id=tenant_id, batch_id=batch_id)
        vault_dir = graphify_vault_dir(tenant_id=tenant_id, batch_id=batch_id, folder_label=batch.folder_label)
        graph_files: list[dict[str, Any]] = []
        vectors_embedded = 0

        try:
            if staging_dir.is_dir():
                for path in sorted(staging_dir.rglob("*")):
                    if not path.is_file():
                        continue
                    if path.stat().st_size > settings.auto_graphify_max_file_bytes:
                        log.warning("auto_graphify.file_skipped_size", filename=path.name)
                        continue
                    rel_path = str(path.relative_to(staging_dir))
                    text = _read_text_file(path)
                    if not text:
                        continue
                    trimmed = text[: settings.auto_graphify_max_content_chars]
                    tags = _extract_tags(rel_path=rel_path, text=trimmed)
                    doc_id = hashlib.sha256(f"{batch_id}:{rel_path}".encode("utf-8")).hexdigest()

                    dest = vault_dir / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    async with aiofiles.open(dest, "w", encoding="utf-8") as handle:
                        await handle.write(trimmed)

                    if settings.hive_mind_enabled and settings.hive_mind_chroma_enabled:
                        try:
                            doc_blob = f"# {path.name}\npath:{rel_path}\n\n{trimmed}"
                            await embed_and_store(
                                doc_blob,
                                {
                                    "source": "auto_graphify",
                                    "tenant_id": str(tenant_id),
                                    "batch_id": str(batch_id),
                                    "vault_rel_path": rel_path,
                                    "doc_id": doc_id[:24],
                                },
                                HIVE_MIND_COLLECTION,
                            )
                            vectors_embedded += 1
                        except (RuntimeError, ValueError, TypeError) as embed_exc:
                            log.warning("auto_graphify.embed_failed", rel_path=rel_path, error=str(embed_exc))

                    self._db.add(
                        KnowledgeItem(
                            tenant_id=tenant_id,
                            source_url=f"auto-graphify://{batch_id}/{rel_path}",
                            source_type="auto_graphify",
                            content_text=trimmed,
                            confidence_score=0.78,
                            topic_tags=tags,
                            decay_factor=1.0,
                            scraped_at=datetime.now(tz=UTC),
                            neo4j_node_id=doc_id,
                        ),
                    )
                    graph_files.append(
                        {
                            "doc_id": doc_id,
                            "rel_path": rel_path,
                            "title": path.name,
                            "excerpt": trimmed[:2400],
                            "tags": tags,
                        },
                    )

            await self._db.flush()
            graph_nodes = 0
            if settings.hive_mind_enabled and graph_files:
                try:
                    graph_nodes = await persist_graphify_ingest_bundle(
                        tenant_id=tenant_id,
                        batch_id=batch_id,
                        folder_label=batch.folder_label,
                        files=graph_files,
                    )
                except Exception as graph_exc:  # noqa: BLE001
                    log.warning("auto_graphify.graph_failed", error=str(graph_exc))

            batch.items_ingested = len(graph_files)
            batch.graph_nodes_created = graph_nodes
            batch.vectors_embedded = vectors_embedded
            batch.vault_rel_path = str(vault_dir.relative_to(Path(settings.hive_mind_vault_root).expanduser())).replace(
                "\\",
                "/",
            )
            pollen = float(batch.items_ingested) * float(settings.auto_graphify_pollen_per_file)
            batch.pollen_earned = await _grant_graphify_pollen(
                self._db,
                tenant_id=tenant_id,
                amount=pollen,
                batch_id=batch_id,
            )
            batch.summary_md = _build_summary_md(
                folder_label=batch.folder_label,
                file_count=batch.file_count,
                items_ingested=batch.items_ingested,
                graph_nodes_created=batch.graph_nodes_created,
                vectors_embedded=batch.vectors_embedded,
                pollen_earned=batch.pollen_earned,
                vault_rel_path=batch.vault_rel_path,
            )
            batch.status = GraphifyStatusORM.COMPLETED
            batch.processed_at = datetime.now(tz=UTC)
            await self._db.flush()
            log.info(
                "auto_graphify.completed",
                items_ingested=batch.items_ingested,
                graph_nodes=batch.graph_nodes_created,
                pollen_earned=batch.pollen_earned,
            )
            return batch
        except Exception as exc:  # noqa: BLE001
            batch.status = GraphifyStatusORM.FAILED
            batch.error_text = str(exc)[:2000]
            batch.processed_at = datetime.now(tz=UTC)
            await self._db.flush()
            log.exception("auto_graphify.failed", error=str(exc))
            raise


__all__ = [
    "AutoGraphifyService",
    "graphify_upload_dir",
    "graphify_vault_dir",
]
