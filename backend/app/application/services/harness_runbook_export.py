"""Operator Runbook export — verified recipe → sellable RUNBOOK bundle."""

from __future__ import annotations

import json

from app.application.services.skill_export import (
    SkillExportFile,
    SkillExportMeta,
    SkillExportResponse,
    build_readme_md,
    build_skill_md,
    recipe_slug,
)
from app.infrastructure.persistence.models.recipe import Recipe


def build_runbook_md(recipe: Recipe) -> str:
    """Human-readable operator runbook from verified recipe."""

    steps = list((recipe.workflow_template or {}).get("steps") or [])
    lines = [
        f"# Operator Runbook — {recipe.name}",
        "",
        "Supervised session playbook — **not** an autonomous agent.",
        "",
        f"{recipe.description or ''}".strip(),
        "",
        "## Prerequisites",
        "",
        "- Queenswarm or Cursor harness with MCP tools connected",
        "- Operator approve gate enabled for publish/financial steps",
        "- Run eval before client delivery",
        "",
        "## Session steps",
        "",
    ]
    for idx, step in enumerate(steps[:12], start=1):
        if not isinstance(step, dict):
            continue
        desc = str(step.get("description") or step.get("name") or f"Step {idx}").strip()
        role = str(step.get("agent_role") or step.get("role") or "supervisor").strip()
        lines.append(f"{idx}. **{role}** — {desc}")
    if not steps:
        lines.extend(
            [
                "1. **supervisor** — Open Agents → New session with goal from SKILL.md",
                "2. **researcher** — Gather context with guardrails",
                "3. **critic** — Verdict APPROVE before external publish",
            ],
        )

    lines.extend(
        [
            "",
            "## Schedule (optional)",
            "",
            "Import into Queenswarm: Knowledge → Recipes → **Schedule routine** (cron/interval).",
            "",
            "## Eval gate",
            "",
            "- Critic must output: `Critic verdict: APPROVE`",
            "- Simulate-first before any live publish",
            "",
        ],
    )
    return "\n".join(lines)


def build_runbook_export_bundle(recipe: Recipe) -> SkillExportResponse:
    """Export verified recipe as Operator Runbook product."""

    slug = f"{recipe_slug(recipe.name)}-runbook"
    folder = slug
    skill_md = build_skill_md(recipe)
    runbook_md = build_runbook_md(recipe)
    install_command = f"npx skills@latest add queenswarm/{recipe_slug(recipe.name)}"
    readme_md = build_readme_md(recipe=recipe, slug=slug, install_command=install_command)
    listing_md = "\n".join(
        [
            f"# {recipe.name} — Operator Runbook",
            "",
            "Verified supervised workflow — orchestrator + sub-agents + eval discipline.",
            "",
            "**Suggested price:** €39–€79",
            "",
            "## Includes",
            "",
            "- RUNBOOK.md — step-by-step operator playbook",
            "- SKILL.md — agentskills.io workflow",
            "- SCHEDULE.template.json — cron/interval starter",
            "",
            recipe.description or "",
            "",
        ],
    )
    schedule_template = {
        "recipe_id": str(recipe.id),
        "recipe_name": recipe.name,
        "schedule_kind": "cron",
        "cron_expr": "0 9 * * 1",
        "runtime_mode": "simulate_first",
        "notes": "Adjust cron in Queenswarm Knowledge → Recipes → Schedule routine",
    }
    meta_json = json.dumps(
        {
            "product_line": "operator_runbook",
            "slug": slug,
            "recipe_id": str(recipe.id),
            "export_version": "1.0",
        },
        indent=2,
    )

    files = [
        SkillExportFile(path=f"{folder}/RUNBOOK.md", content=runbook_md),
        SkillExportFile(path=f"{folder}/SKILL.md", content=skill_md),
        SkillExportFile(path=f"{folder}/README.md", content=readme_md),
        SkillExportFile(path=f"{folder}/LISTING.md", content=listing_md),
        SkillExportFile(
            path=f"{folder}/SCHEDULE.template.json",
            content=json.dumps(schedule_template, indent=2) + "\n",
        ),
        SkillExportFile(path=f"{folder}/meta.json", content=meta_json + "\n"),
    ]

    total = recipe.success_count + recipe.fail_count
    meta = SkillExportMeta(
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        slug=slug,
        verified=recipe.verified_at is not None,
        verified_at=recipe.verified_at,
        success_rate=float(recipe.success_count / total) if total else 0.0,
        avg_pollen_earned=float(recipe.avg_pollen_earned or 0.0),
        success_count=int(recipe.success_count or 0),
        fail_count=int(recipe.fail_count or 0),
        topic_tags=list(recipe.topic_tags or []),
    )

    return SkillExportResponse(
        meta=meta,
        files=files,
        install_command=install_command,
        install_hint="Sell on Gumroad — RUNBOOK + SKILL + schedule template.",
        publish=None,
    )


__all__ = ["build_runbook_export_bundle", "build_runbook_md"]
