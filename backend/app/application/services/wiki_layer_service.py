"""Karpathy-style Wiki Layer — raw inventory, compiled wiki, gardener sweeps, token telemetry."""

from __future__ import annotations

import io
import re
import uuid
import zipfile
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.curated_memory_service import CuratedMemoryService
from app.core.config import settings
from app.core.logging import get_logger
from app.domain.memory.curated import CuratedFileKind
from app.infrastructure.persistence.models.dump_sleep_batch import DumpSleepBatchORM, DumpSleepStatusORM
from app.infrastructure.persistence.models.knowledge import KnowledgeItem
from app.infrastructure.persistence.models.recipe import Recipe
from app.infrastructure.persistence.models.tenant import Tenant
from app.infrastructure.persistence.models.wiki_layer import (
    WikiGardenerRunORM,
    WikiGardenerStatusORM,
    WikiLayerPageORM,
)

logger = get_logger(__name__)

WIKI_LAYER_BUCKET = "wiki_layer"
RetrievalTier = Literal["wiki_only", "deep_raw"]
DEFAULT_RETRIEVAL_TIER: RetrievalTier = "wiki_only"

_PROJECT_SECTION_RE = re.compile(
    r"(?is)(?:^|\n)#+\s*project\s+briefs?\s*\n(.*?)(?=\n#+\s|\Z)",
)
_RAW_SUMMARY_CAP = 420
_WIKI_PAGE_SLUGS: tuple[tuple[str, str], ...] = (
    ("operator-context", "Operator context"),
    ("project-briefs", "Project briefs"),
    ("forager-insights", "Forager insights"),
    ("verified-recipes", "Verified recipes"),
)


def normalize_retrieval_tier(raw: object) -> RetrievalTier:
    """Coerce stored value to supported retrieval tier."""

    text = str(raw or DEFAULT_RETRIEVAL_TIER).strip().lower()
    if text in {"wiki_only", "deep_raw"}:
        return text  # type: ignore[return-value]
    return DEFAULT_RETRIEVAL_TIER


def _wiki_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get(WIKI_LAYER_BUCKET)
    return dict(bucket) if isinstance(bucket, dict) else {}


def wiki_config_from_tenant(tenant: Tenant | None) -> dict[str, Any]:
    """Read wiki layer config from tenant operator_settings."""

    bucket = _wiki_bucket(tenant.operator_settings if tenant is not None else None)
    telemetry = bucket.get("telemetry")
    return {
        "retrieval_tier": normalize_retrieval_tier(bucket.get("retrieval_tier")),
        "telemetry": dict(telemetry) if isinstance(telemetry, dict) else {},
    }


async def load_wiki_config(session: AsyncSession, *, tenant_id: object | None) -> dict[str, Any]:
    """Load effective wiki layer config for tenant."""

    if not settings.wiki_layer_enabled:
        return {
            "retrieval_tier": "deep_raw",
            "telemetry": {},
            "feature_enabled": False,
        }
    if tenant_id is None:
        return {
            "retrieval_tier": DEFAULT_RETRIEVAL_TIER,
            "telemetry": {},
            "feature_enabled": True,
        }
    tenant = await session.get(Tenant, tenant_id)
    cfg = wiki_config_from_tenant(tenant)
    cfg["feature_enabled"] = True
    return cfg


def merge_wiki_patch(operator_settings: dict[str, Any] | None, patch: dict[str, Any]) -> dict[str, Any]:
    """Apply partial wiki_layer patch to tenant operator_settings."""

    root = dict(operator_settings or {})
    bucket = _wiki_bucket(root)
    if "retrieval_tier" in patch:
        bucket["retrieval_tier"] = normalize_retrieval_tier(patch["retrieval_tier"])
    if "telemetry" in patch and isinstance(patch["telemetry"], dict):
        existing = dict(bucket.get("telemetry") or {})
        existing.update(patch["telemetry"])
        bucket["telemetry"] = existing
    root[WIKI_LAYER_BUCKET] = bucket
    return root


def _truncate(text: str, cap: int) -> str:
    if len(text) <= cap:
        return text
    return text[: cap - 1] + "…"


def _extract_project_briefs(instructions_md: str) -> str:
    """Pull PROJECT briefs section from curated instructions."""

    body = instructions_md or ""
    match = _PROJECT_SECTION_RE.search(body)
    if match:
        return match.group(1).strip()
    if len(body) <= 2400:
        return body.strip()
    return _truncate(body.strip(), 2400)


def _summarize_knowledge_item(row: KnowledgeItem) -> str:
    text = (row.content_text or "").strip().replace("\n", " ")
    tags = ", ".join(row.topic_tags[:6]) if row.topic_tags else ""
    prefix = f"[{row.source_type}]"
    if tags:
        prefix = f"{prefix} ({tags})"
    return f"{prefix} {_truncate(text, _RAW_SUMMARY_CAP)}"


class WikiLayerService:
    """Compile hot-tier wiki pages, inventory raw sources, run Gardener sweeps."""

    def __init__(self, *, db: AsyncSession) -> None:
        self._db = db

    async def list_raw_sources(
        self,
        tenant_id: uuid.UUID,
        *,
        limit: int = 32,
    ) -> list[dict[str, Any]]:
        """Return read-only descriptors for cold-tier raw sources."""

        since = datetime.now(tz=UTC) - timedelta(days=14)
        ki_rows = list(
            (
                await self._db.scalars(
                    select(KnowledgeItem)
                    .where(
                        KnowledgeItem.tenant_id == tenant_id,
                        KnowledgeItem.scraped_at >= since,
                    )
                    .order_by(desc(KnowledgeItem.scraped_at))
                    .limit(limit),
                )
            ).all(),
        )
        dump_rows = list(
            (
                await self._db.scalars(
                    select(DumpSleepBatchORM)
                    .where(
                        DumpSleepBatchORM.tenant_id == tenant_id,
                        DumpSleepBatchORM.status == DumpSleepStatusORM.COMPLETED,
                    )
                    .order_by(desc(DumpSleepBatchORM.created_at))
                    .limit(min(12, limit)),
                )
            ).all(),
        )

        out: list[dict[str, Any]] = []
        for row in ki_rows:
            out.append(
                {
                    "layer": "raw",
                    "source_type": "knowledge_item",
                    "id": str(row.id),
                    "label": row.source_type,
                    "preview": _truncate(row.content_text.replace("\n", " "), 180),
                    "scraped_at": row.scraped_at.isoformat(),
                    "verified": row.verified_at is not None,
                },
            )
        for row in dump_rows:
            out.append(
                {
                    "layer": "raw",
                    "source_type": "dump_sleep",
                    "id": str(row.id),
                    "label": f"Dump & Sleep ({row.file_count} files)",
                    "preview": _truncate(row.briefing_md.replace("\n", " "), 180),
                    "scraped_at": row.created_at.isoformat() if row.created_at else None,
                    "verified": row.status == DumpSleepStatusORM.COMPLETED,
                },
            )
        return out

    async def list_wiki_pages(self, tenant_id: uuid.UUID) -> list[WikiLayerPageORM]:
        """Return compiled wiki pages for tenant."""

        return list(
            (
                await self._db.scalars(
                    select(WikiLayerPageORM)
                    .where(WikiLayerPageORM.tenant_id == tenant_id)
                    .order_by(WikiLayerPageORM.slug),
                )
            ).all(),
        )

    async def get_overview(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        """Return three-zone overview: raw, wiki, instructions."""

        curated = CuratedMemoryService(db=self._db)
        bundle = await curated.get_bundle(tenant_id)
        pages = await self.list_wiki_pages(tenant_id)
        raw = await self.list_raw_sources(tenant_id)
        instructions_md = bundle.get(CuratedFileKind.INSTRUCTIONS, "")
        wiki_chars = sum(int(p.char_count) for p in pages)
        curated_chars = sum(len(v or "") for v in bundle.values())

        return {
            "zones": {
                "raw": {
                    "count": len(raw),
                    "items": raw[:16],
                    "description": "Forager scrape, Dump & Sleep, knowledge_items — deep research only.",
                },
                "wiki": {
                    "count": len(pages),
                    "char_count": wiki_chars,
                    "pages": [
                        {
                            "slug": p.slug,
                            "title": p.title,
                            "char_count": p.char_count,
                            "version": p.version,
                            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                        }
                        for p in pages
                    ],
                    "description": "Compiled hot tier — injected every Queen prompt.",
                },
                "instructions": {
                    "char_count": len(instructions_md),
                    "preview": _truncate(instructions_md.replace("\n", " "), 320),
                    "description": "Behavioral instructions from curated memory.",
                },
            },
            "curated_prefix_chars": curated_chars,
            "wiki_chars": wiki_chars,
        }

    async def get_page(self, tenant_id: uuid.UUID, slug: str) -> WikiLayerPageORM | None:
        """Return one wiki page by slug."""

        return await self._db.scalar(
            select(WikiLayerPageORM).where(
                WikiLayerPageORM.tenant_id == tenant_id,
                WikiLayerPageORM.slug == slug,
            ),
        )

    async def render_wiki_prompt_block(self, tenant_id: uuid.UUID) -> str:
        """Render compact wiki block for hot-tier Queen prompt injection."""

        if not settings.wiki_layer_enabled:
            return ""
        pages = await self.list_wiki_pages(tenant_id)
        if not pages:
            return ""

        cap = settings.wiki_layer_max_prompt_chars
        lines = ["=== WIKI LAYER (hot tier) ==="]
        used = len(lines[0]) + 1
        for page in pages:
            header = f"## {page.title}"
            body = (page.content_md or "").strip()
            chunk = f"{header}\n{body}\n"
            if used + len(chunk) > cap:
                remaining = cap - used - len(header) - 4
                if remaining > 80:
                    lines.append(header)
                    lines.append(_truncate(body, remaining))
                break
            lines.append(header)
            lines.append(body)
            used += len(chunk)
        lines.append("=== END WIKI LAYER ===")
        return "\n".join(lines)

    async def run_gardener(
        self,
        tenant_id: uuid.UUID,
        *,
        agent_id: str = "wiki-gardener",
        swarm_id: str = "",
        task_id: str = "",
    ) -> WikiGardenerRunORM:
        """Sweep raw sources into compiled wiki pages (deterministic, no LLM)."""

        run = WikiGardenerRunORM(
            tenant_id=tenant_id,
            status=WikiGardenerStatusORM.RUNNING,
            summary_md="",
            stats={},
            pages_updated=0,
            raw_scanned=0,
        )
        self._db.add(run)
        await self._db.flush()

        logger.info(
            "wiki_layer.gardener.start",
            agent_id=agent_id,
            swarm_id=swarm_id,
            task_id=task_id or str(run.id),
            tenant_id=str(tenant_id),
        )

        try:
            curated = CuratedMemoryService(db=self._db)
            bundle = await curated.get_bundle(tenant_id)
            raw_items = await self._fetch_recent_knowledge(tenant_id)
            recipes = await self._fetch_verified_recipes(limit=8)
            pages_updated = 0

            operator_ctx = self._compile_operator_context(bundle)
            pages_updated += await self._upsert_page(
                tenant_id,
                slug="operator-context",
                title="Operator context",
                content_md=operator_ctx,
                source_refs=[{"type": "curated_memory", "kinds": ["mission", "soul", "ideal_state"]}],
            )

            project_md = _extract_project_briefs(bundle.get(CuratedFileKind.INSTRUCTIONS, ""))
            pages_updated += await self._upsert_page(
                tenant_id,
                slug="project-briefs",
                title="Project briefs",
                content_md=project_md or "_No project briefs yet — add under Curated memory → Instructions._",
                source_refs=[{"type": "curated_memory", "kind": "instructions"}],
            )

            insight_lines = [_summarize_knowledge_item(row) for row in raw_items[:12]]
            forager_md = "\n".join(f"- {line}" for line in insight_lines) if insight_lines else "_No recent forager insights._"
            pages_updated += await self._upsert_page(
                tenant_id,
                slug="forager-insights",
                title="Forager insights",
                content_md=forager_md,
                source_refs=[{"type": "knowledge_item", "ids": [str(r.id) for r in raw_items[:12]]}],
            )

            recipe_lines = [f"- **{r.name}** — { _truncate(r.description or '', 120)}" for r in recipes]
            recipes_md = "\n".join(recipe_lines) if recipe_lines else "_No verified recipes yet._"
            pages_updated += await self._upsert_page(
                tenant_id,
                slug="verified-recipes",
                title="Verified recipes",
                content_md=recipes_md,
                source_refs=[{"type": "recipe", "ids": [str(r.id) for r in recipes]}],
            )

            run.status = WikiGardenerStatusORM.COMPLETED
            run.pages_updated = pages_updated
            run.raw_scanned = len(raw_items)
            run.summary_md = (
                f"Updated {pages_updated} wiki page(s) from {len(raw_items)} raw knowledge item(s) "
                f"and {len(recipes)} verified recipe(s)."
            )
            run.stats = {
                "raw_knowledge_items": len(raw_items),
                "verified_recipes": len(recipes),
                "page_slugs": [slug for slug, _ in _WIKI_PAGE_SLUGS],
            }
            run.pollen_awarded = settings.wiki_layer_gardener_pollen if pages_updated > 0 else 0.0
            run.completed_at = datetime.now(tz=UTC)
            await self._db.flush()

            logger.info(
                "wiki_layer.gardener.completed",
                agent_id=agent_id,
                swarm_id=swarm_id,
                task_id=task_id or str(run.id),
                pages_updated=pages_updated,
                raw_scanned=len(raw_items),
            )
            return run
        except Exception as exc:
            run.status = WikiGardenerStatusORM.FAILED
            run.summary_md = f"Gardener failed: {exc}"
            run.completed_at = datetime.now(tz=UTC)
            await self._db.flush()
            logger.exception(
                "wiki_layer.gardener.failed",
                agent_id=agent_id,
                swarm_id=swarm_id,
                task_id=task_id or str(run.id),
            )
            raise

    async def record_prompt_telemetry(
        self,
        tenant_id: uuid.UUID,
        *,
        curated_prefix_chars: int,
        wiki_chars: int,
        rag_chunks: int,
        raw_fallback_hits: int,
    ) -> None:
        """Persist last prompt assembly telemetry for Costs / Agent OS dashboard."""

        tenant = await self._db.get(Tenant, tenant_id)
        if tenant is None:
            return
        patch = {
            "telemetry": {
                "curated_prefix_chars": curated_prefix_chars,
                "wiki_chars": wiki_chars,
                "rag_chunks": rag_chunks,
                "raw_fallback_hits": raw_fallback_hits,
                "recorded_at": datetime.now(tz=UTC).isoformat(),
            },
        }
        tenant.operator_settings = merge_wiki_patch(tenant.operator_settings, patch)
        await self._db.flush()

    async def export_obsidian_vault(self, tenant_id: uuid.UUID) -> bytes:
        """Export Brain Pack + wiki pages as Obsidian-compatible ZIP."""

        curated = CuratedMemoryService(db=self._db)
        bundle = await curated.get_bundle(tenant_id)
        brain_md = curated.render_brain_pack_export(bundle)
        pages = await self.list_wiki_pages(tenant_id)

        buf = io.BytesIO()
        moc_lines = ["# Queenswarm Vault MOC", "", "## Brain Pack", "- [[Brain-Pack]]", "- [[Instructions]]", "", "## Wiki"]
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("Brain-Pack.md", brain_md)
            zf.writestr("Instructions.md", bundle.get(CuratedFileKind.INSTRUCTIONS, ""))
            for page in pages:
                safe_name = re.sub(r"[^\w\-]+", "-", page.slug).strip("-") or "page"
                wikilink = f"[[{safe_name}]]"
                moc_lines.append(f"- {wikilink} — {page.title}")
                body = f"# {page.title}\n\n{page.content_md}\n\n---\nBacklinks: [[Vault-MOC]]\n"
                zf.writestr(f"wiki/{safe_name}.md", body)
            zf.writestr("Vault-MOC.md", "\n".join(moc_lines) + "\n")
            zf.writestr(
                "README-Obsidian-Sync.md",
                "# Obsidian sync (OBS1)\n\n"
                "1. Unzip into your vault.\n"
                "2. Edit wiki/*.md locally — use Integrations → Obsidian sync to ingest.\n"
                "3. Vault-MOC uses wikilinks for bidirectional navigation.\n",
            )
        return buf.getvalue()

    async def latest_gardener_run(self, tenant_id: uuid.UUID) -> WikiGardenerRunORM | None:
        """Return most recent gardener run for tenant."""

        return await self._db.scalar(
            select(WikiGardenerRunORM)
            .where(WikiGardenerRunORM.tenant_id == tenant_id)
            .order_by(desc(WikiGardenerRunORM.created_at))
            .limit(1),
        )

    def _compile_operator_context(self, bundle: dict[CuratedFileKind, str]) -> str:
        mission = _truncate((bundle.get(CuratedFileKind.MISSION) or "").strip(), 800)
        ideal = _truncate((bundle.get(CuratedFileKind.IDEAL_STATE) or "").strip(), 600)
        soul = _truncate((bundle.get(CuratedFileKind.SOUL) or "").strip(), 600)
        skills = _truncate((bundle.get(CuratedFileKind.SKILLS_HIERARCHY) or "").strip(), 400)
        parts = []
        if mission:
            parts.append(f"**Mission**\n{mission}")
        if ideal:
            parts.append(f"**Ideal state**\n{ideal}")
        if soul:
            parts.append(f"**Soul**\n{soul}")
        if skills:
            parts.append(f"**Skills**\n{skills}")
        return "\n\n".join(parts) if parts else "_Operator context empty — seed Brain Pack._"

    async def _fetch_recent_knowledge(self, tenant_id: uuid.UUID, *, limit: int = 24) -> list[KnowledgeItem]:
        since = datetime.now(tz=UTC) - timedelta(days=7)
        return list(
            (
                await self._db.scalars(
                    select(KnowledgeItem)
                    .where(
                        KnowledgeItem.tenant_id == tenant_id,
                        KnowledgeItem.scraped_at >= since,
                    )
                    .order_by(desc(KnowledgeItem.scraped_at))
                    .limit(limit),
                )
            ).all(),
        )

    async def _fetch_verified_recipes(self, *, limit: int) -> list[Recipe]:
        return list(
            (
                await self._db.scalars(
                    select(Recipe)
                    .where(Recipe.verified_at.isnot(None))
                    .order_by(desc(Recipe.success_count))
                    .limit(limit),
                )
            ).all(),
        )

    async def _upsert_page(
        self,
        tenant_id: uuid.UUID,
        *,
        slug: str,
        title: str,
        content_md: str,
        source_refs: list[dict[str, Any]],
    ) -> int:
        """Upsert one wiki page; return 1 if written, 0 if unchanged."""

        safe_content = (content_md or "").strip()
        char_count = len(safe_content)
        row = await self.get_page(tenant_id, slug)
        if row is not None and row.content_md == safe_content:
            return 0
        if row is None:
            row = WikiLayerPageORM(
                tenant_id=tenant_id,
                slug=slug,
                title=title,
                content_md=safe_content,
                source_refs=source_refs,
                char_count=char_count,
                version=1,
                updated_at=datetime.now(tz=UTC),
            )
            self._db.add(row)
        else:
            row.title = title
            row.content_md = safe_content
            row.source_refs = source_refs
            row.char_count = char_count
            row.version = int(row.version) + 1
            row.updated_at = datetime.now(tz=UTC)
        await self._db.flush()
        return 1


__all__ = [
    "DEFAULT_RETRIEVAL_TIER",
    "RetrievalTier",
    "WIKI_LAYER_BUCKET",
    "WikiLayerService",
    "load_wiki_config",
    "merge_wiki_patch",
    "normalize_retrieval_tier",
    "wiki_config_from_tenant",
]
