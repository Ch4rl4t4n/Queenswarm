"""Eval-as-a-Service — heuristic + optional LLM critic for buyer workflows."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.application.services.skill_factory_export_harness import build_eval_report_md
from app.application.services.skill_factory_quality_gate import (
    critic_approved_factory,
    evaluate_factory_outputs,
    validate_skill_markdown,
)
from app.application.services.skill_factory_sellable import assess_tenant_skill_sellable
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM

logger = get_logger(__name__)


class HarnessEvalRequest(BaseModel):
    """Operator or future Gumroad buyer eval input."""

    model_config = ConfigDict(extra="forbid")

    workflow_markdown: str = Field(min_length=40, max_length=80_000)
    title: str = Field(default="Submitted workflow", max_length=200)
    run_llm_critic: bool = False


class HarnessEvalResultOut(BaseModel):
    """Eval-as-a-Service result."""

    model_config = ConfigDict(extra="ignore")

    passed: bool
    tier: str
    score: float
    issues: list[str] = Field(default_factory=list)
    critic_approved: bool
    skill_valid: bool
    eval_report_md: str
    recommended_gumroad_price_eur_cents: int = 2900


def _shim_skill(*, title: str, markdown: str) -> TenantSkillORM:
    """Minimal skill row for sellable assessment."""

    return TenantSkillORM(
        slug="eval-submission",
        title=title[:200],
        description="Eval-as-a-Service submission",
        markdown_body=markdown,
        version="1.0.0",
        priority=50,
        roles=[],
        keywords=[],
        source="eval_service",
        is_active=True,
    )


async def run_harness_eval(body: HarnessEvalRequest) -> HarnessEvalResultOut:
    """Evaluate submitted workflow markdown — Eval-as-a-Service core."""

    md = body.workflow_markdown.strip()
    skill_ok, skill_issues = validate_skill_markdown(md)

    critic_output = ""
    if body.run_llm_critic and settings.skill_factory_enabled:
        critic_output = await _llm_critic_verdict(workflow_md=md, title=body.title)
    elif body.run_llm_critic:
        critic_output = "Critic verdict: REJECT\nReason: LLM critic disabled."

    if body.run_llm_critic and critic_output:
        quality = evaluate_factory_outputs(
            skill_markdown=md,
            critic_output=critic_output,
            coder_output=md[:4000],
        )
    else:
        quality = evaluate_factory_outputs(
            skill_markdown=md,
            critic_output=(
                "Critic verdict: APPROVE\nHeuristic pre-check only."
                if skill_ok and len(md) >= 120
                else "Critic verdict: REJECT\nHeuristic failed structure check."
            ),
            coder_output=md[:4000],
        )

    shim = _shim_skill(title=body.title, markdown=md)
    forge_quality = {
        "quality_gate_passed": quality.passed,
        "critic_approved": quality.critic_approved,
        "skill_valid": quality.skill_valid,
        "issues": list(quality.issues),
    }
    assessment = assess_tenant_skill_sellable(shim, forge_quality=forge_quality)
    report = build_eval_report_md(shim, forge_quality=forge_quality, assessment=assessment)

    logger.info(
        "harness_eval.completed",
        agent_id="harness_eval",
        passed=quality.passed,
        tier=assessment.tier,
        score=assessment.score,
        llm_critic=body.run_llm_critic,
    )

    return HarnessEvalResultOut(
        passed=quality.passed and assessment.recommended_for_launch,
        tier=assessment.tier,
        score=assessment.score,
        issues=list(dict.fromkeys([*quality.issues, *skill_issues, *assessment.issues])),
        critic_approved=quality.critic_approved,
        skill_valid=quality.skill_valid,
        eval_report_md=report,
        recommended_gumroad_price_eur_cents=2900 if quality.passed else 1900,
    )


async def _llm_critic_verdict(*, workflow_md: str, title: str) -> str:
    """Optional LLM critic for paid eval tier."""

    from app.application.services.factory_llm_readiness_service import run_factory_llm_smoke
    from app.core.database import async_session
    from app.core.llm_router import LiteLLMRouter

    async with async_session() as session:
        smoked = await run_factory_llm_smoke(session)
        if not smoked.smoke_ok:
            return f"Critic verdict: REJECT\nReason: LLM unavailable ({smoked.smoke_error or 'smoke failed'})."

    from app.core.config import settings as app_settings

    router = LiteLLMRouter()
    model_name = app_settings.workflow_breaker_primary_model
    prompt = (
        "You are a harness critic. Review this workflow/SKILL for production sale.\n"
        "End with exactly one line: Critic verdict: APPROVE or Critic verdict: REJECT\n\n"
        f"Title: {title}\n\n{workflow_md[:12000]}"
    )
    try:
        async with async_session() as session:
            content, _cost = await router.complete_single_model(
                session,
                model_name=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
                task_id="harness_eval_critic",
                swarm_id="harness_products",
            )
        raw = str(content or "").strip()
        if not critic_approved_factory(raw) and "REJECT" not in raw.upper():
            return f"{raw}\n\nCritic verdict: REJECT\nReason: missing explicit APPROVE."
        return raw
    except Exception as exc:
        return f"Critic verdict: REJECT\nReason: LLM error ({exc})."


__all__ = ["HarnessEvalRequest", "HarnessEvalResultOut", "run_harness_eval"]
