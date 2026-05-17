"""OutputEngine façade — Ballroom + dashboard surfaces call into :mod:`service`."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.agents.executor import hive_llm_credentials_ready
from app.core.config import Settings, get_settings
from app.domain.hive_mind.ingest import HiveMindExtras
from app.domain.hive_mind.service import HiveMindService
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable
from app.domain.outputs.service import derive_title, persist_final_deliverable, slugify_fragment


def build_fallback_structured(
    *,
    brief_excerpt: str,
    manager_slugs: list[str],
    post_meta: dict[str, Any],
) -> dict[str, Any]:
    """Structured JSON scaffold when orch SECTION_JSON is absent."""

    return {
        "format": "queenswarm.final_deliverable.v1",
        "brief_excerpt": brief_excerpt[:2000],
        "manager_templates": manager_slugs,
        "reflection": {"post_mortem": post_meta},
    }


class OutputEngine:
    """Thin static API consumed by Ballroom mission + regenerate routes."""

    @staticmethod
    async def create_final_deliverable(
        session: AsyncSession,
        *,
        lineage_id: uuid.UUID,
        markdown_body: str,
        structured: dict[str, Any],
        title_hint: str,
        slug_hint: str,
        tags: list[str],
        voice_script: str | None,
        dashboard_user_id: uuid.UUID | None,
        ballroom_session_id: uuid.UUID | None,
        mission_id: uuid.UUID | None,
        source_task_id: uuid.UUID | None = None,
        settings: Settings | None = None,
        hive_mind_extras: HiveMindExtras | None = None,
    ) -> TaskFinalDeliverable:
        """Archive canonical Markdown + structured JSON artefacts."""

        cfg = settings or get_settings()
        row = await persist_final_deliverable(
            session,
            lineage_id=lineage_id,
            dashboard_user_id=dashboard_user_id,
            ballroom_session_id=ballroom_session_id,
            mission_id=mission_id,
            source_task_id=source_task_id,
            slug_hint=slug_hint,
            title_hint=title_hint or derive_title(markdown_body.strip(), slug_hint),
            markdown_body=markdown_body,
            structured=structured,
            tags=tags,
            voice_script=voice_script,
            settings=cfg,
        )

        if cfg.hive_mind_enabled:
            await HiveMindService.ingest_final_deliverable(
                row=row,
                settings=cfg,
                extras=hive_mind_extras,
                swarm_id=str(ballroom_session_id) if ballroom_session_id else None,
                task_id=str(mission_id or lineage_id),
                agent_id="output-engine",
            )

        return row

    @staticmethod
    async def regenerate_via_llm(
        session: AsyncSession,
        *,
        lineage_id: uuid.UUID,
        dashboard_user_id: uuid.UUID,
        instruction: str,
        prior_markdown: str,
        prior_structured: dict[str, Any],
        ballroom_session_id: uuid.UUID | None,
        mission_id: uuid.UUID | None,
        tags: list[str],
        swarm_id_label: str,
        task_slug: str,
        settings: Settings | None = None,
    ) -> TaskFinalDeliverable:
        """Create version N+1 by asking LiteLLM to revise artefacts."""

        if not hive_llm_credentials_ready():
            msg = "LLM credentials missing — cannot regenerate deliverable automatically."
            raise RuntimeError(msg)

        from app.core.llm_router import LiteLLMRouter

        router = LiteLLMRouter()
        blended = "# Prior markdown\n" + prior_markdown[:9000]
        blended += "\n\n# Prior JSON\n```json\n" + str(prior_structured)[:4000]
        blended += "\n```\n"
        user_prompt = (
            instruction.strip()
            + "\n\nProduce the same three orch sections SECTION_TEXT SECTION_JSON SECTION_VOICE."
        )

        merged_system = (
            "You revise final hive deliverables. Output SECTION_TEXT Markdown, SECTION_JSON object, SECTION_VOICE narration."
        )
        raw, _cost = await router.decompose(
            session,
            system_prompt=merged_system,
            user_payload=blended + "\nOPERATOR NOTES:\n" + user_prompt,
            swarm_id=swarm_id_label,
            task_id=task_slug,
        )
        from app.domain.outputs.parsing import coalesce_json_text, split_orchestrator_deliverable_sections

        parts = split_orchestrator_deliverable_sections(raw)
        md = parts.get("text") or prior_markdown
        structured_next = coalesce_json_text(parts.get("json"))
        voice = parts.get("voice")
        merged_structured = dict(prior_structured)
        merged_structured.update(structured_next)

        headline = derive_title(md, "Regenerated deliverable")

        cfg = settings or get_settings()
        row = await persist_final_deliverable(
            session,
            lineage_id=lineage_id,
            dashboard_user_id=dashboard_user_id,
            ballroom_session_id=ballroom_session_id,
            mission_id=mission_id,
            source_task_id=None,
            slug_hint=slugify_fragment(headline),
            title_hint=headline,
            markdown_body=md,
            structured=merged_structured,
            tags=tags + ["regenerated"],
            voice_script=voice,
            settings=cfg,
        )

        if cfg.hive_mind_enabled:
            await HiveMindService.ingest_final_deliverable(
                row=row,
                settings=cfg,
                extras=HiveMindExtras(manager_template_slugs=["regenerated_via_llm"]),
                swarm_id=swarm_id_label,
                task_id=task_slug,
                agent_id="output-regenerate",
            )

        return row


__all__ = ["OutputEngine", "build_fallback_structured"]
