"""HiveMind orchestrator — ingestion, retrieval, capped exports."""

from __future__ import annotations

import io
import json
import uuid
import zipfile
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chroma_client import (
    HIVE_MIND_COLLECTION,
    embed_and_store,
    semantic_search,
)
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.application.services.selective_recall import (
    RecallMode,
    effective_prompt_char_budget,
    normalize_recall_mode,
    rank_vector_hits,
    score_vector_similarity,
)
from app.application.services.wiki_layer_service import RetrievalTier, normalize_retrieval_tier
from app.domain.hive_mind.graph import (
    bounded_operator_graph_snapshot,
    neighbor_snapshot_for_prompt,
    persist_hive_graph_bundle,
    vault_document_recall_for_prompt,
)
from app.domain.hive_mind.ingest import (
    HiveMindExtras,
    extract_auto_tags,
    persist_vault_projection,
    summarise_deliverable,
)
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable

logger = get_logger(__name__)


def _truncate(text: str, cap: int) -> str:
    """Clip UTF-8 safe-ish text for embeddings / prompts."""

    if len(text) <= cap:
        return text
    return text[: cap - 1] + "…"


class HiveMindService:
    """Shared swarm memory façade — Postgres deliverables hydrate vault + Neo4j + vectors."""

    @staticmethod
    async def ingest_final_deliverable(
        *,
        row: TaskFinalDeliverable,
        settings: Settings | None = None,
        extras: HiveMindExtras | None = None,
        swarm_id: str | None = None,
        agent_id: str | None = None,
        task_id: str | None = None,
    ) -> None:
        """Persist Obsidian-compatible artefacts + constellation graph (fail-open)."""

        cfg = settings or get_settings()
        if not cfg.hive_mind_enabled:
            return

        bag = extras or HiveMindExtras()
        sid = swarm_id or (str(row.ballroom_session_id) if row.ballroom_session_id else "")
        aid = agent_id or "output-engine"
        tid = task_id or str(row.lineage_id)
        structured = dict(row.structured_json) if isinstance(row.structured_json, dict) else {}
        summary_heur, insight_body = summarise_deliverable(structured, row.markdown_body)
        reflection_text = bag.reflection_excerpt or ""
        if not reflection_text:
            refl = structured.get("reflection") if isinstance(structured.get("reflection"), dict) else {}
            rex = refl.get("post_mortem") if isinstance(refl, dict) else None
            if isinstance(rex, dict):
                excerpt = rex.get("reflection_excerpt")
                reflection_text = str(excerpt).strip() if excerpt else ""

        merged_tags = extract_auto_tags(row.markdown_body, list(row.tags or []))

        vault_rel = None
        try:
            vault_rel = await persist_vault_projection(
                row=row,
                summary=summary_heur,
                reflection_excerpt=reflection_text.strip()[:8000],
                insight_note=_truncate(insight_body, 6200),
                vault_root_str=cfg.hive_mind_vault_root,
                folder_slug_hint=row.slug,
            )
            if vault_rel is None:
                logger.warning(
                    "hive_mind.vault_skipped",
                    agent_id=aid,
                    swarm_id=sid,
                    task_id=tid,
                    deliverable_id=str(row.id),
                )
        except OSError as exc:
            logger.warning(
                "hive_mind.vault_failed",
                agent_id=aid,
                swarm_id=sid,
                task_id=tid,
                error=str(exc),
            )

        if cfg.hive_mind_chroma_enabled:
            blob = (
                f"# {row.title}\n{summary_heur}\n\n"
                f"### Tags\n{', '.join(merged_tags)}\n\n"
                f"{_truncate(row.markdown_body, cfg.hive_mind_embed_max_chars)}"
            )
            meta_flat: dict[str, Any] = {
                "deliverable_id": str(row.id),
                "lineage_id": str(row.lineage_id),
                "version": row.version,
                "dashboard_user_id": str(row.dashboard_user_id or ""),
                "mission_id": str(row.mission_id or ""),
                "tags_joined": ",".join(merged_tags[:24]),
                "hive_vault_relpath": vault_rel or "",
            }
            try:
                vector_doc_id = await embed_and_store(blob, meta_flat, HIVE_MIND_COLLECTION)
                logger.info(
                    "hive_mind.vector_written",
                    agent_id=aid,
                    swarm_id=sid,
                    task_id=tid,
                    vector_id=vector_doc_id,
                )
            except Exception as exc:
                logger.warning(
                    "hive_mind.vector_failed",
                    agent_id=aid,
                    swarm_id=sid,
                    task_id=tid,
                    error=str(exc),
                )

        dash_uid_str = str(row.dashboard_user_id) if row.dashboard_user_id else ""

        graph_tags = merged_tags[:32]
        try:
            await persist_hive_graph_bundle(
                deliverable_id=row.id,
                lineage_id=row.lineage_id,
                version=row.version,
                title=row.title,
                slug=row.slug,
                summary=_truncate(summary_heur, 2200),
                tags=graph_tags,
                dashboard_user_id_str=dash_uid_str,
                reflection_excerpt=_truncate(reflection_text, 7900),
                insight_summary=_truncate(summary_heur, 620),
                insight_body=_truncate(insight_body, 4800),
                mission_id=row.mission_id,
                manager_slugs=list(bag.manager_template_slugs or []),
                source_task_id=row.source_task_id,
                markdown_excerpt=_truncate(row.markdown_body, 2400),
            )
        except Exception as exc:
            logger.warning(
                "hive_mind.neo4j_failed",
                agent_id=aid,
                swarm_id=sid,
                task_id=tid,
                error=str(exc),
            )

    @staticmethod
    async def query_for_prompt(
        *,
        relevance_to_current_task: str,
        settings: Settings | None = None,
        swarm_id: str = "",
        task_id: str = "",
        agent_id: str = "",
        tenant_id: uuid.UUID | None = None,
        recall_mode: RecallMode | str | None = None,
        token_budget_chars: int = 0,
        retrieval_tier: RetrievalTier | str | None = None,
    ) -> str:
        """Return Markdown snippet for orch / manager conditioning (vectors + graph neighbours)."""

        cfg = settings or get_settings()
        if not cfg.hive_mind_enabled or not relevance_to_current_task.strip():
            return ""

        tier = normalize_retrieval_tier(
            retrieval_tier if retrieval_tier is not None else "wiki_only",
        )
        mode = normalize_recall_mode(
            recall_mode
            if recall_mode is not None
            else (cfg.hive_mind_default_recall_mode if cfg.hive_mind_selective_recall_enabled else "full"),
        )
        char_budget = effective_prompt_char_budget(
            recall_mode=mode,
            tenant_budget=token_budget_chars,
            settings_max_prompt=cfg.hive_mind_max_prompt_chars,
            selective_max_chars=cfg.hive_mind_selective_recall_max_chars,
        )

        clipped_query = relevance_to_current_task.strip()[:4000]
        lines: list[str] = []
        pruned = 0

        if tier == "wiki_only":
            return ""

        max_hits = (
            cfg.hive_mind_selective_recall_max_hits
            if mode == "selective"
            else min(cfg.hive_mind_max_query_hits_vector, 12)
        )
        min_similarity = cfg.hive_mind_selective_recall_min_similarity if mode == "selective" else 0.0

        hints: list[dict[str, Any]] = []
        if cfg.hive_mind_chroma_enabled:
            try:
                search_cap = max_hits * 3 if mode == "selective" else min(cfg.hive_mind_max_query_hits_vector, 12)
                hints = await semantic_search(
                    clipped_query,
                    HIVE_MIND_COLLECTION,
                    n_results=search_cap,
                )
            except Exception as exc:
                logger.warning(
                    "hive_mind.query_vector_failed",
                    agent_id=agent_id or "hive-mind-query",
                    swarm_id=swarm_id,
                    task_id=task_id,
                    error=str(exc),
                )

        if mode == "selective":
            hints, pruned = rank_vector_hits(
                hints,
                max_hits=max_hits,
                min_similarity=min_similarity,
            )
        else:
            hints = hints[:max_hits]

        deliverable_hints: list[str] = []
        for hit in hints:
            blob = hit.get("document")
            snippet = ""
            if isinstance(blob, str) and blob.strip():
                max_snip = 280 if mode == "selective" else 420
                snippet = _truncate(blob.strip().replace("\n", " "), max_snip)
            meta = dict(hit.get("metadata") or {})
            did = meta.get("deliverable_id")
            similarity = score_vector_similarity(hit.get("distance"))
            sim_label = f"(sim≈{similarity:.2f})" if mode == "selective" else ""
            if not sim_label:
                try:
                    if hit.get("distance") is not None:
                        sim_label = f"(sim≈{similarity:.2f})"
                except (TypeError, ValueError):
                    sim_label = ""

            headline = snippet or ""
            summary_line = headline or "vector hit"
            if did:
                deliverable_hints.append(str(did))
                summary_line += f" id={did}"
            lines.append(f"- {sim_label} {summary_line}".strip())

        graph_breadth = 2 if mode == "selective" else cfg.hive_mind_max_graph_neighbor_breadth
        uniq_ids = list(dict.fromkeys(deliverable_hints))[: (3 if mode == "selective" else 8)]
        try:
            graph_lines = await neighbor_snapshot_for_prompt(
                deliverable_ids=uniq_ids,
                breadth=graph_breadth,
            )
            if graph_lines:
                lines.extend(["", "### Graph neighbourhoods", *graph_lines[:graph_breadth]])
        except Exception as exc:
            logger.warning(
                "hive_mind.query_graph_failed",
                agent_id=agent_id or "hive-mind-query",
                swarm_id=swarm_id,
                task_id=task_id,
                error=str(exc),
            )

        if mode == "selective" and tenant_id is not None:
            try:
                vault_lines = await vault_document_recall_for_prompt(
                    tenant_id=tenant_id,
                    query=clipped_query,
                    limit=cfg.hive_mind_selective_vault_doc_limit,
                )
                if vault_lines:
                    lines.extend(["", "### Vault documents (selective)", *vault_lines])
            except Exception as exc:
                logger.warning(
                    "hive_mind.query_vault_failed",
                    agent_id=agent_id or "hive-mind-query",
                    swarm_id=swarm_id,
                    task_id=task_id,
                    error=str(exc),
                )

        if not lines:
            return ""

        header = (
            "## HiveMind selective recall · graph-neighbour RAG\n"
            if mode == "selective"
            else "## HiveMind recall · vector + correlations\n"
        )
        if mode == "selective" and pruned > 0:
            lines.append(f"\n_auto-pruned {pruned} low-similarity hits_")
        body = header + "\n".join(lines)
        return _truncate(body, char_budget)

    @staticmethod
    async def export_zip_bytes(
        *,
        session: AsyncSession,
        dashboard_user_id: uuid.UUID,
        settings: Settings | None = None,
    ) -> bytes:
        """Bundle manifests + Markdown + capped graph snapshot (RAM-safe buffer)."""

        cfg = settings or get_settings()
        stmt = (
            select(TaskFinalDeliverable)
            .where(TaskFinalDeliverable.dashboard_user_id == dashboard_user_id)
            .order_by(TaskFinalDeliverable.created_at.desc())
            .limit(120)
        )
        rows_list = list((await session.scalars(stmt)).all())

        buffer = io.BytesIO()
        total = 0
        max_zip = cfg.hive_mind_export_max_zip_bytes
        dash_uid_str = str(dashboard_user_id)
        vault_root = Path(cfg.hive_mind_vault_root).resolve()

        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for row in rows_list:
                fname = f"deliverables/{row.slug}_v{row.version}.md"
                payload_txt = row.markdown_body.encode("utf-8")
                if total + len(payload_txt) > max_zip:
                    break
                zf.writestr(fname, payload_txt)
                total += len(payload_txt)

                meta_fname = f"deliverables/{row.slug}_v{row.version}.json"
                meta_blob = json.dumps(
                    {
                        "deliverable_id": str(row.id),
                        "lineage_id": str(row.lineage_id),
                        "version": row.version,
                        "title": row.title,
                        "structured": row.structured_json,
                        "tags": row.tags,
                    },
                    indent=2,
                    default=str,
                ).encode("utf-8")
                if total + len(meta_blob) > max_zip:
                    break
                zf.writestr(meta_fname, meta_blob)
                total += len(meta_blob)

            if vault_root.exists():
                scanned = 0
                for path in vault_root.glob("**/memory.md"):
                    if scanned >= 80:
                        break
                    scanned += 1
                    manifest_path = path.parent / "manifest.json"
                    if not manifest_path.is_file():
                        continue
                    manifest_raw = manifest_path.read_bytes()
                    manifest_obj = json.loads(manifest_raw.decode("utf-8"))
                    if manifest_obj.get("dashboard_user_id") != dash_uid_str:
                        continue
                    rel = path.relative_to(vault_root)
                    arc = Path("vault_obsidian_mirror") / rel
                    txt = path.read_bytes()
                    if total + len(txt) + len(manifest_raw) > max_zip:
                        break
                    zf.writestr(str(arc), txt)
                    zf.writestr(str(arc.parent / "manifest.json"), manifest_raw)
                    total += len(txt) + len(manifest_raw)

            try:
                graph_blob = json.dumps(
                    await bounded_operator_graph_snapshot(
                        dashboard_user_id=dash_uid_str,
                        limit_nodes=cfg.hive_mind_max_graph_export_nodes,
                    ),
                    indent=2,
                    default=str,
                ).encode("utf-8")
                if total + len(graph_blob) <= max_zip:
                    zf.writestr("neo4j_graph_snapshot.json", graph_blob)
                    total += len(graph_blob)
            except Exception:
                logger.warning(
                    "hive_mind.export_graph_failed",
                    agent_id=str(dashboard_user_id),
                    swarm_id="export",
                    task_id="hive-mind",
                )

        return buffer.getvalue()


__all__ = ["HiveMindService"]
