"""Verified Niche Harness export artifacts — HARNESS.md, EVAL_REPORT.md, TOOLS.json."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.application.services.skill_factory_sellable import SkillSellableAssessment, assess_tenant_skill_sellable
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM

_DEFAULT_MCP_TOOLS = [
    {
        "slug": "tavily_search",
        "purpose": "Research niche signals and competitor pages before workflow steps.",
        "required": False,
    },
    {
        "slug": "gumroad_rest",
        "purpose": "Optional — draft/publish listing when seller token configured.",
        "required": False,
    },
]


def build_tools_json(
    skill: TenantSkillORM,
    *,
    opportunity: SkillOpportunityORM | None = None,
    extra_tools: list[dict[str, Any]] | None = None,
) -> str:
    """MCP-oriented tool map for harness buyers."""

    keywords = [str(k).strip().lower() for k in list(skill.keywords or []) if str(k).strip()]
    tools: list[dict[str, Any]] = list(_DEFAULT_MCP_TOOLS)
    if any("seo" in k or "content" in k for k in keywords):
        tools.append(
            {
                "slug": "serper_search",
                "purpose": "SERP and content research for SEO pipeline steps.",
                "required": False,
            },
        )
    if any("github" in k or "cursor" in k for k in keywords):
        tools.append(
            {
                "slug": "github_rest",
                "purpose": "Export teaser repos and open PRs for skill distribution.",
                "required": False,
            },
        )
    if extra_tools:
        tools.extend(extra_tools)

    payload = {
        "schema_version": "1.0",
        "harness_type": "verified_niche_harness",
        "skill_slug": skill.slug,
        "niche": opportunity.niche if opportunity else None,
        "mcp_tools": tools,
        "integration_path": "Queenswarm Integrations → Hub → connect slugs listed above",
        "cursor_path": "Copy SKILL.md to .cursor/skills/ or load via Skill Library import",
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def build_harness_md(
    skill: TenantSkillORM,
    *,
    opportunity: SkillOpportunityORM | None = None,
) -> str:
    """Context-engineering contract for buyers."""

    niche = opportunity.niche if opportunity else skill.title
    price = f"€{(opportunity.suggested_price_eur_cents / 100):.2f}" if opportunity else "see LISTING.md"
    return "\n".join(
        [
            f"# Harness — {skill.title}",
            "",
            "This pack is a **Verified Niche Harness**: context contract + workflow + eval discipline.",
            "It is not a generic prompt template.",
            "",
            "## When to use",
            "",
            f"- Operator runs **{niche}** workflows with simulate-first guardrails.",
            "- You want a production checklist, not autonomous \"build any agent\" magic.",
            "",
            "## When not to use",
            "",
            "- One-click autonomný agent bez human approve.",
            "- Horizontálny marketplace skill bez niche kontextu.",
            "",
            "## Context layers",
            "",
            "1. **SKILL.md** — agentskills.io workflow body (load into Cursor / Claude / Queenswarm).",
            "2. **TOOLS.json** — MCP connector slugs this harness expects.",
            "3. **EVAL_REPORT.md** — what the factory critic verified.",
            "4. **HIVE.md** — tenant memory overlay hints.",
            "",
            "## Orchestrator pattern",
            "",
            "```",
            "Supervisor goal",
            "  → Researcher (context gather)",
            "  → Coder (SKILL draft)",
            "  → Critic (verdict APPROVE / REJECT)",
            "  → Simulate before external publish",
            "```",
            "",
            "## Price anchor",
            "",
            f"Suggested: **{price}** (Gumroad / manual upload).",
            "",
            "## Maintenance",
            "",
            "Re-run factory eval when your LLM or MCP stack changes. Harness beats model.",
            "",
        ],
    )


def build_eval_report_md(
    skill: TenantSkillORM,
    *,
    forge_quality: dict[str, Any] | None = None,
    assessment: SkillSellableAssessment | None = None,
) -> str:
    """Eval discipline artifact bundled with every export."""

    assessed = assessment or assess_tenant_skill_sellable(skill, forge_quality=forge_quality)
    now = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Eval report — {skill.title}",
        "",
        f"Generated: {now}",
        "",
        "## Summary",
        "",
        f"- **Tier:** {assessed.tier}",
        f"- **Score:** {assessed.score:.2f}",
        f"- **Recommended for launch:** {'yes' if assessed.recommended_for_launch else 'no'}",
        "",
        "## Quality gate",
        "",
    ]
    if forge_quality:
        lines.append(f"- quality_gate_passed: `{forge_quality.get('quality_gate_passed')}`")
        lines.append(f"- critic_approved: `{forge_quality.get('critic_approved')}`")
        lines.append(f"- skill_valid: `{forge_quality.get('skill_valid')}`")
        issues = forge_quality.get("issues")
        if isinstance(issues, list) and issues:
            lines.append(f"- forge_issues: {', '.join(str(i) for i in issues[:8])}")
    else:
        lines.append("- Forge payload not linked — heuristic assessment only.")

    if assessed.issues:
        lines.append("")
        lines.append("## Assessment issues")
        lines.append("")
        for issue in assessed.issues:
            lines.append(f"- `{issue}`")

    lines.extend(
        [
            "",
            "## Buyer checklist",
            "",
            "- [ ] Load SKILL.md into your harness (Cursor / Queenswarm / Claude Code).",
            "- [ ] Connect MCP tools from TOOLS.json (optional but recommended).",
            "- [ ] Run one dry-run session before live publish or client delivery.",
            "- [ ] Do not ship if critic verdict would be REJECT on your stack.",
            "",
        ],
    )
    return "\n".join(lines)


def build_mcp_setup_md(
    skill: TenantSkillORM,
    *,
    opportunity: SkillOpportunityORM | None = None,
) -> str:
    """MCP Connector Starter Kit setup guide."""

    niche = opportunity.niche if opportunity else skill.title
    return "\n".join(
        [
            f"# MCP Setup — {skill.title}",
            "",
            "MCP Connector Starter Kit — connect tools before running the harness.",
            "",
            f"**Niche:** {niche}",
            "",
            "## Steps",
            "",
            "1. Open Queenswarm → **Integrations → Hub** (or Claude Desktop / Cursor MCP settings).",
            "2. Install connectors listed in `TOOLS.json` (start with optional slugs).",
            "3. **Test connection** on each connector before running SKILL workflow.",
            "4. Load `SKILL.md` into your harness Skill Library.",
            "5. Run one **simulate-first** session; check `EVAL_REPORT.md` criteria.",
            "",
            "## Cursor / Claude Desktop",
            "",
            "- Add MCP server entries from vendor docs for each slug in TOOLS.json.",
            "- Never enable publish/financial tools without operator approve.",
            "",
            "## Support tier (Gumroad)",
            "",
            "Offer 30-day update on TOOLS.json when MCP vendors change endpoints.",
            "",
        ],
    )


__all__ = [
    "build_eval_report_md",
    "build_harness_md",
    "build_mcp_setup_md",
    "build_tools_json",
]
