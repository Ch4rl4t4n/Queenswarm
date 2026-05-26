"""Supervisor session enrichment — Execution Studio policy, domain, manual excerpt."""

from __future__ import annotations

from typing import Any, Literal

from app.application.services.execution_studio_manual import build_execution_studio_manual
from app.core.config import get_settings
from app.infrastructure.persistence.models.tenant import Tenant

from app.application.services.queen_maintainer.maintainer_guard import MAINTAINER_LANE_KEY

ExecutionDomain = Literal["external", "internal", "hybrid"] | None

ExecutionMode = Literal["draft", "simulate", "live"]

_EXTERNAL_TOKENS: tuple[str, ...] = (
    "connect",
    "connector",
    "notion",
    "gmail",
    "slack",
    "instagram",
    "post ",
    "publish",
    "api ",
    "oauth",
    "marketplace",
    "composio",
    "nango",
)

_INTERNAL_TOKENS: tuple[str, ...] = (
    "codebase",
    "refactor",
    "maintainer",
    "pull request",
    " github",
    "dependency",
    "tech debt",
    "pytest",
    "implement feature",
    "fix bug",
    "execution studio",
)


def detect_execution_domain(goal: str) -> ExecutionDomain:
    """Infer whether a supervisor goal targets external, internal, or hybrid execution."""

    lowered = goal.strip().lower()
    external = any(token in lowered for token in _EXTERNAL_TOKENS)
    internal = any(token in lowered for token in _INTERNAL_TOKENS)
    if external and internal:
        return "hybrid"
    if internal:
        return "internal"
    if external:
        return "external"
    return None


def _policy_from_tenant(tenant: Tenant | None) -> dict[str, Any]:
    """Read execution policy from tenant settings without importing execution_studio."""

    root = dict(tenant.operator_settings or {}) if tenant is not None else {}
    bucket = dict(root.get("execution_studio") or {}) if isinstance(root.get("execution_studio"), dict) else {}
    mode_raw = str(bucket.get("default_mode") or "simulate").strip().lower()
    mode: ExecutionMode = mode_raw if mode_raw in {"draft", "simulate", "live"} else "simulate"
    codebase_raw = str(bucket.get("codebase_default_mode") or mode).strip().lower()
    codebase_mode: ExecutionMode = codebase_raw if codebase_raw in {"draft", "simulate", "live"} else mode
    return {
        "default_mode": mode,
        "live_requires_approval": bool(bucket.get("live_requires_approval", True)),
        "simulate_allows_read_calls": bool(bucket.get("simulate_allows_read_calls", True)),
        "codebase_default_mode": codebase_mode,
        "live_codebase_requires_approval": bool(bucket.get("live_codebase_requires_approval", True)),
        "codebase_pr_only": True,
    }


def augment_skill_slugs_for_execution(
    goal: str,
    *,
    skill_slugs: list[str] | None,
) -> list[str] | None:
    """Auto-attach execution-studio skill when goal implies real execution."""

    if not get_settings().execution_studio_enabled:
        return skill_slugs
    if detect_execution_domain(goal) is None:
        return skill_slugs
    merged = list(skill_slugs or [])
    if "execution-studio" not in merged:
        merged.append("execution-studio")
    return merged


def build_execution_prompt_block(*, domain: ExecutionDomain, policy: dict[str, Any]) -> str:
    """Compact prompt block injected into supervisor sub-agents."""

    manual = build_execution_studio_manual(section_id="agent_reference")
    section = manual.get("section") if manual.get("found") else None
    agent_ref = str((section or {}).get("content_md") or manual.get("agent_quick_reference") or "")[:1200]

    domain_line = f"Detected execution domain: {domain or 'unspecified'}."
    mode_line = (
        f"Default mode: {policy.get('default_mode')} · "
        f"codebase mode: {policy.get('codebase_default_mode')} · "
        f"live approval: {policy.get('live_requires_approval')}."
    )
    return (
        "## Execution Studio (governed execution)\n"
        f"{domain_line}\n{mode_line}\n"
        "Consult manual: GET /api/v1/execution-studio/manual\n\n"
        f"{agent_ref}"
    )[:4000]


def execution_prompt_from_summary(context_summary: dict[str, Any] | None) -> str:
    """Extract Execution Studio prompt block from supervisor context_summary."""

    if not isinstance(context_summary, dict):
        return ""
    block = context_summary.get("execution_studio")
    if not isinstance(block, dict):
        return ""
    return str(block.get("prompt_block") or "").strip()


def enrich_supervisor_session_summary(
    summary: dict[str, object],
    *,
    tenant: Tenant | None,
    goal: str,
    roles: list[str],
) -> dict[str, object]:
    """Merge Execution Studio runtime hints into supervisor context_summary."""

    if not get_settings().execution_studio_enabled:
        return summary

    policy = _policy_from_tenant(tenant)
    domain = detect_execution_domain(goal)
    enriched = dict(summary)
    if enriched.get(MAINTAINER_LANE_KEY):
        policy = dict(policy)
        policy["default_mode"] = "simulate"
        policy["codebase_default_mode"] = "simulate"
        policy["live_codebase_requires_approval"] = True
        policy["codebase_pr_only"] = True
    enriched["execution_studio"] = {
        "enabled": True,
        "execution_domain": domain,
        "policy": policy,
        "roles": list(roles),
        "manual_api": "/api/v1/execution-studio/manual",
        "prompt_block": build_execution_prompt_block(domain=domain, policy=policy),
    }
    return enriched


__all__ = [
    "augment_skill_slugs_for_execution",
    "build_execution_prompt_block",
    "detect_execution_domain",
    "enrich_supervisor_session_summary",
    "execution_prompt_from_summary",
]
