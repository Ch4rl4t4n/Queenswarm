"""Real LiteLLM execution for supervisor sub-agents (replaces harness stubs)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.agent_prompt_templates import (
    _CODEBASE_SCOUT_BEE,
    _HIVEMIND_DUTY,
    _SHARED_GUARDRAILS,
    _WORLD_SIGNALS_BEE,
    _WORKER_OUTPUT_CONTRACT,
    AGENT_PROMPT_REGISTRY,
)
from app.application.services.queen_maintainer.maintainer_guard import is_maintainer_session
from app.application.services.supervisor.hivemind_insight_ingest import ingest_supervisor_insights
from app.application.services.supervisor.hivemind_verify import (
    build_critic_verify_user_block,
    finalize_hivemind_ingest_after_critic,
    is_hivemind_verify_session,
    load_researcher_draft,
)
from app.application.services.supervisor.skills import SkillLibrary
from app.application.services.supervisor.spawner import infer_manager_slug_for_role
from app.core.config import settings
from app.core.llm_router import LiteLLMRouter
from app.core.logging import get_logger
from app.domain.agents.executor import (
    hive_llm_credentials_ready,
    markdown_no_llm_fallback,
    prioritize_research_connector_tools,
    run_tool_bundle,
)
from app.domain.hive_mind.service import HiveMindService
from app.infrastructure.connectors.dynamic.service import merged_static_and_dynamic_allowlist
from app.infrastructure.persistence.models.supervisor_session import SubAgentSession, SupervisorSession

logger = get_logger(__name__)

_ROLE_BEE: dict[str, str] = {
    "researcher": "World Signals Bee",
    "coder": "Codebase Scout Bee",
    "designer": "Content Draft Bee",
}

_CRITIC_SYSTEM = f"""\
You are **Critic** in a supervisor session — HiveMind verification lane.

═══ ROLE ═══
Review researcher drafts BEFORE they enter HiveMind. Block unverified claims.

═══ METHOD ═══
1. Challenge every claim without a source URL or HiveMind node id.
2. Flag duplicate insights already in HiveMind memory.
3. End with EXACTLY one verdict line (required):
   - `## Verification verdict: APPROVED`
   - `## Verification verdict: REJECTED — <reason>`

{_WORKER_OUTPUT_CONTRACT}

{_SHARED_GUARDRAILS}
- REJECTED drafts must NOT reach HiveMind ingest.
- Never approve live destructive actions. Simulate-first only.
"""


def resolve_system_prompt_for_role(role: str) -> str:
    """Map dashboard sub-agent role to curated bee system prompt."""

    key = role.strip().lower()
    bee_name = _ROLE_BEE.get(key)
    if bee_name and bee_name in AGENT_PROMPT_REGISTRY:
        return AGENT_PROMPT_REGISTRY[bee_name].system_prompt
    if key == "researcher":
        return _WORLD_SIGNALS_BEE
    if key == "coder":
        return _CODEBASE_SCOUT_BEE
    if key == "critic":
        return _CRITIC_SYSTEM
    return (
        f"You are a **{role}** sub-agent in a Queenswarm supervisor session.\n\n"
        f"{_WORKER_OUTPUT_CONTRACT}\n{_HIVEMIND_DUTY}\n{_SHARED_GUARDRAILS}"
    )


def _tools_for_role(role: str, *, allowlist: frozenset[str]) -> list[Any]:
    """Select free-tier research tools + optional Notion simulate for HiveMind writes."""

    key = role.strip().lower()
    bundle: list[Any] = []
    if key in {"researcher", "critic", "designer"}:
        bundle.extend(["grokipedia", "wikipedia"])
    if key == "researcher":
        bundle.append({"name": "rss", "args": {"url": "https://hnrss.org/frontpage", "max_items": 5}})
    if "notion_workspace" in allowlist and key in {"researcher", "coder", "critic"}:
        bundle.append(
            {
                "name": "mcp_invoke",
                "args": {
                    "connector_slug": "notion_workspace",
                    "tool_name": "invoke",
                    "arguments": {"mode": "simulate"},
                },
            },
        )
    return bundle


async def execute_supervisor_sub_agent_llm(
    db: AsyncSession,
    *,
    supervisor_session: SupervisorSession,
    sub_agent: SubAgentSession,
    goal: str,
    selected_skills: list[str],
    skill_library: SkillLibrary | None,
    retrieval_prompt: str,
    meta_reasoning_prompt: str,
    hint: str | None,
    attempt: int,
) -> str:
    """Run tools + LiteLLM for one supervisor sub-agent attempt."""

    loader = skill_library or SkillLibrary()
    role = str(sub_agent.role or "researcher").strip()
    summary = dict(supervisor_session.context_summary or {})
    raw_goal = str(summary.get("raw_goal") or goal).strip()
    sub_goal = str((sub_agent.short_memory or {}).get("sub_goal") or raw_goal).strip()

    if not settings.supervisor_sub_agent_llm_enabled or not hive_llm_credentials_ready():
        return markdown_no_llm_fallback(
            agent_name=role,
            user_prompt=sub_goal,
            tool_results={},
        )

    hive_memory = ""
    if settings.hive_mind_enabled and supervisor_session.tenant_id is not None:
        try:
            hive_memory = await HiveMindService.query_for_prompt(
                relevance_to_current_task=sub_goal[:2000],
                tenant_id=supervisor_session.tenant_id,
                swarm_id=str(supervisor_session.id),
                task_id=str(sub_agent.id),
                agent_id=role,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "supervisor_llm.hive_memory_failed",
                agent_id=role,
                swarm_id=str(supervisor_session.id),
                task_id=str(sub_agent.id),
                error=str(exc),
            )

    skill_prompt = await loader.build_prompt_block_async(
        selected_skills,
        lazy_fetch=settings.skill_lazy_reference_fetch_enabled,
    )
    manager_slug = infer_manager_slug_for_role(role)
    allowlist_list = await merged_static_and_dynamic_allowlist(
        db,
        manager_template_slug=manager_slug,
    )
    allow_tokens = frozenset(str(tok).strip().lower() for tok in allowlist_list if str(tok).strip())

    tool_specs = prioritize_research_connector_tools(
        _tools_for_role(role, allowlist=allow_tokens),
        manager_slug=manager_slug,
        allowlist_tokens=allow_tokens,
        agent_name=role,
        oc={},
    )
    tool_results = await run_tool_bundle(
        db,
        tool_specs,
        agent_name=role,
        output_config={},
        executor_context={
            "connector_allowlist": list(allow_tokens),
            "manager_slug": manager_slug,
            "task_id": str(sub_agent.id),
            "tenant_id": str(supervisor_session.tenant_id) if supervisor_session.tenant_id else None,
        },
    )

    verify_lane = is_hivemind_verify_session(summary)
    researcher_draft_block = ""
    if verify_lane and role.lower() == "critic":
        draft = str(summary.get("researcher_draft_for_verify") or "").strip()
        if not draft:
            draft = await load_researcher_draft(db, supervisor_session_id=supervisor_session.id)
        if draft:
            researcher_draft_block = f"\n\n{build_critic_verify_user_block(researcher_draft=draft)}"

    execute_instruction = (
        "Execute now. Include at least one `[INSIGHT]` HiveMind write-back with tag "
        "`hivemind-candidate` when you surface verified findings."
    )
    if verify_lane and role.lower() == "researcher":
        execute_instruction = (
            "Execute now. Produce a detailed researcher draft with `[INSIGHT]` candidates tagged "
            "`hivemind-candidate` in the markdown. The critic will verify before HiveMind ingest — "
            "include source URLs for every claim."
        )

    hint_block = f"\n\n## Self-heal hint (attempt {attempt})\n{hint.strip()}" if hint and hint.strip() else ""
    user_payload = (
        f"## Session goal\n{raw_goal[:4000]}\n\n"
        f"## Your sub-goal ({role})\n{sub_goal[:2400]}\n\n"
        f"## Skills\n{skill_prompt[:3500]}\n\n"
        f"## Retrieved context\n{retrieval_prompt[:3500]}\n\n"
        f"## HiveMind memory\n{hive_memory[:3500] if hive_memory else '(none)'}\n\n"
        f"## Meta reasoning rubric\n{meta_reasoning_prompt[:2500]}"
        f"{researcher_draft_block}"
        f"{hint_block}\n\n"
        f"{execute_instruction}"
    )

    router = LiteLLMRouter()
    model_override: str | None = None
    if is_maintainer_session(summary):
        overrides = summary.get("maintainer_model_overrides")
        if isinstance(overrides, dict):
            picked = overrides.get(role) or overrides.get("default")
            if isinstance(picked, str) and picked.strip():
                model_override = picked.strip()

    system_prompt = resolve_system_prompt_for_role(role)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_payload},
    ]

    try:
        if model_override:
            _response, llm_output, _used, _cost = await router._acompletion_with_model(  # noqa: SLF001
                db,
                model_name=model_override,
                messages=messages,
                swarm_id=str(supervisor_session.id),
                task_id=None,
            )
        else:
            llm_output, _cost = await router.complete_with_fallback_messages(
                db,
                messages=messages,
                swarm_id=str(supervisor_session.id),
                task_id=None,
            )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "supervisor_llm.failed",
            agent_id=role,
            swarm_id=str(supervisor_session.id),
            task_id=str(sub_agent.id),
            error=str(exc),
        )
        return f"{role} LLM execution error: {str(exc)[:400]}"

    llm_output = (llm_output or "").strip()
    insight_ids: list[str] = []
    if supervisor_session.tenant_id is not None and llm_output:
        if verify_lane and role.lower() == "researcher":
            summary["researcher_draft_for_verify"] = llm_output[:50_000]
            supervisor_session.context_summary = summary
            await db.flush()
        elif verify_lane and role.lower() == "critic":
            approved, insight_ids = await finalize_hivemind_ingest_after_critic(
                db,
                supervisor_session=supervisor_session,
                critic_output=llm_output,
                researcher_draft=str(summary.get("researcher_draft_for_verify") or ""),
            )
            if not approved:
                llm_output = (
                    f"{llm_output.rstrip()}\n\n---\nHiveMind ingest **skipped** — critic verdict not APPROVED."
                )
        elif "publish pack" in role.lower():
            from app.application.services.publish_pack import try_archive_publish_pack_from_session_output

            draft = str(summary.get("researcher_draft_for_verify") or summary.get("publish_pack_draft") or "")
            combined = f"{draft}\n\n{llm_output}".strip() if draft else llm_output
            ctx_verify = str((supervisor_session.context_summary or {}).get("hivemind_verify_status") or "")
            await try_archive_publish_pack_from_session_output(
                db,
                supervisor_session=supervisor_session,
                combined_output=combined,
                critic_excerpt=llm_output if "critic" in role.lower() else "",
                verified=ctx_verify == "approved",
            )
            summary["publish_pack_draft"] = llm_output[:50_000]
            supervisor_session.context_summary = summary
            await db.flush()
        else:
            insight_ids = await ingest_supervisor_insights(
                db,
                tenant_id=supervisor_session.tenant_id,
                supervisor_session_id=supervisor_session.id,
                sub_agent_role=role,
                llm_output=llm_output,
            )

    tool_summary = ""
    if tool_results:
        tool_summary = "\n\n---\nTool highlights:\n" + "\n".join(
            f"- {key}: {str(val)[:280]}" for key, val in list(tool_results.items())[:4]
        )

    insight_note = ""
    if insight_ids:
        insight_note = f"\n\nHiveMind insights ingested: {len(insight_ids)} (tags: hivemind-candidate)."

    return f"{llm_output}{tool_summary}{insight_note}".strip()


__all__ = [
    "execute_supervisor_sub_agent_llm",
    "resolve_system_prompt_for_role",
]
