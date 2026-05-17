"""Orchestrator + Review-style post-mortem persisting imitation-friendly artifacts."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from neo4j.exceptions import Neo4jError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.agents.managers.registry import get_manager_template
from app.core.config import Settings
from app.core.logging import get_logger
from app.core.neo4j_client import create_knowledge_node, record_imitation
from app.domain.recipes.library import autosave_verified_workflow
from app.domain.recipes.manager_template_recipes import BallroomPostMortemOutline
from app.common.schemas.recipes_write import RecipeCreateBody
from app.application.services.recipe_write import RecipeWriteConflictError

logger = get_logger(__name__)


def _snippet(text: str, limit: int) -> str:
    """Trim user-visible prose for compact metadata."""

    data = text.strip()
    return data[:limit]


async def summarize_ballroom_post_mortem_via_llm(
    session: AsyncSession,
    *,
    orchestrator_prompt: str,
    review_lane_prompt: str,
    stitched_deliverables: str,
    user_brief: str,
    swarm_id: str,
    correlation_id: str,
) -> str:
    """Ask LiteLLM for markdown post-mortem (falls back to deterministic stub without keys)."""

    from app.domain.agents.executor import hive_llm_credentials_ready
    from app.core.llm_router import LiteLLMRouter

    if not hive_llm_credentials_ready():
        return "## Post-mortem (offline)\nLiteLLM keys missing — archival stub only."

    blended_system = (
        f"{review_lane_prompt.strip()[:6000]}\n\n---\n## Orchestrator alignment\n"
        f"{orchestrator_prompt.strip()[:2000]}"
    )
    user_block = (
        "Write a concise post-mortem Markdown with sections: Highlights, Risks, "
        "Recipes-to-clone next time.\nKeep under ~600 words.\n\n"
        f"### Original brief\n{user_brief.strip()[:4000]}\n\n"
        f"### Manager bundle\n{stitched_deliverables.strip()[:10_000]}\n"
    )
    router = LiteLLMRouter()
    raw, _cost = await router.decompose(
        session,
        system_prompt=blended_system,
        user_payload=user_block,
        swarm_id=swarm_id,
        task_id=correlation_id,
    )
    return raw.strip()


def _parse_outline_from_json(raw_llm_json: str) -> BallroomPostMortemOutline | None:
    """Attempt JSON extraction — optional enrichment path."""

    text = raw_llm_json.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text.strip(), flags=re.IGNORECASE)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
        if isinstance(data, dict):
            merged = dict(data)
            if "summary_markdown" not in merged:
                merged["summary_markdown"] = merged.get("post_mortem") or merged.get("summary") or raw_llm_json
            return BallroomPostMortemOutline.model_validate(merged)
    except (json.JSONDecodeError, ValidationError):
        return None
    return None


async def run_ballroom_post_mortem_persistence(
    session: AsyncSession,
    *,
    settings: Settings,
    orchestrator_prompt: str,
    preview_digest: str,
    user_brief: str,
    stitched_deliverables: str,
    manager_template_slugs: list[str],
    mission_id: uuid.UUID,
    session_id: uuid.UUID,
    orchestrator_agent_id: uuid.UUID,
) -> dict[str, Any]:
    """Persist neo4j knowledge + Recipe row when mutations are enabled."""

    meta: dict[str, Any] = {"mission_id": str(mission_id), "skipped": False}
    if not settings.hive_ballroom_post_mortem_enabled:
        meta["skipped"] = True
        meta["reason"] = "hive_ballroom_post_mortem_enabled=false"
        return meta

    try:
        review_prompt = get_manager_template("review_quality").prompt_text()
    except KeyError:
        review_prompt = "You are the Review & Quality lane."

    summary_md = await summarize_ballroom_post_mortem_via_llm(
        session,
        orchestrator_prompt=orchestrator_prompt,
        review_lane_prompt=review_prompt,
        stitched_deliverables=stitched_deliverables,
        user_brief=user_brief,
        swarm_id=str(session_id),
        correlation_id=f"post_mortem-{mission_id}",
    )

    outline = _parse_outline_from_json(summary_md)
    digest_text = outline.summary_markdown if outline else summary_md

    from app.application.services.swarm_manager_selection import recipe_tag_for_manager_slug

    tags = ["qs.post_mortem", "qs.phase0.5.ballroom"]
    tags.extend(recipe_tag_for_manager_slug(slug) for slug in manager_template_slugs)

    neo_id: str | None = None
    try:
        neo_id = await create_knowledge_node(
            content=digest_text.strip()[:12_000],
            source=f"ballroom_post_mortem::{mission_id}",
            confidence=0.72,
            topic_tags=list(dict.fromkeys(tags)),
        )
    except Neo4jError as exc:
        logger.warning(
            "swarm_post_mortem.neo4j_failed",
            agent_id=str(orchestrator_agent_id),
            swarm_id=str(session_id),
            task_id=str(mission_id),
            error=str(exc),
        )

    meta["neo4j_knowledge_node_id"] = neo_id

    recipe_id_str: str | None = None
    if settings.recipe_catalog_mutations_enabled:
        wf_template: dict[str, Any]
        if outline:
            wf_template = outline.as_workflow_bundle(
                mission_id=str(mission_id),
                preview_digest=preview_digest,
                lane_slugs=manager_template_slugs,
            )
        else:
            wf_template = {
                "kind": "ballroom_post_mortem",
                "revision": "phase0.5",
                "mission_id": str(mission_id),
                "manager_template_slugs": list(manager_template_slugs),
                "breaker_digest": preview_digest.strip()[:4000],
                "post_mortem": digest_text.strip()[:12_000],
            }
        suffix = str(mission_id).split("-", maxsplit=1)[0]
        body = RecipeCreateBody(
            name=f"Ballroom post-mortem {suffix}",
            description=_snippet(digest_text, 420),
            topic_tags=list(dict.fromkeys(tags)),
            workflow_template=wf_template,
            created_by_agent_id=orchestrator_agent_id,
            mark_verified=False,
        )
        try:
            recipe = await autosave_verified_workflow(
                session,
                body,
                swarm_id=str(session_id),
                task_id=str(mission_id),
                created_by_agent_id=orchestrator_agent_id,
            )
            recipe_id_str = str(recipe.id)
        except RecipeWriteConflictError:
            logger.info(
                "swarm_post_mortem.recipe_name_collision",
                agent_id=str(orchestrator_agent_id),
                swarm_id=str(session_id),
                task_id=str(mission_id),
            )
        except SQLAlchemyError as exc:
            logger.warning(
                "swarm_post_mortem.recipe_persist_failed",
                agent_id=str(orchestrator_agent_id),
                swarm_id=str(session_id),
                task_id=str(mission_id),
                error=str(exc),
            )
        meta["recipe_id"] = recipe_id_str
        if recipe_id_str and neo_id:
            try:
                await record_imitation(
                    copier_id=f"agent:{orchestrator_agent_id}",
                    copied_id=f"manager:review_quality",
                    recipe_id=recipe_id_str,
                )
            except Neo4jError:
                logger.warning(
                    "swarm_post_mortem.imitation_edge_failed",
                    agent_id=str(orchestrator_agent_id),
                    swarm_id=str(session_id),
                    task_id=str(mission_id),
                )

    meta["post_mortem_chars"] = len(digest_text)
    meta["reflection_excerpt"] = _snippet(digest_text, 4000)
    return meta


__all__ = [
    "run_ballroom_post_mortem_persistence",
    "summarize_ballroom_post_mortem_via_llm",
]
