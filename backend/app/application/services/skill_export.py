"""Export verified Recipe Library rows as Cursor/Claude-compatible skill bundles."""

from __future__ import annotations

import json
import re
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.hive_md_generator import generate_recipe_hive_md, meta_json_preview
from app.application.services.recipe_catalog import list_recipe_catalog_rows
from app.application.services.skill_marketplace_policy import is_premium_recipe, resolve_skill_price_cents
from app.application.services.skill_publish_assets import build_listing_md, build_publish_guide, build_readme_md
from app.application.services.supervisor.skills import SkillLibrary, SkillSnippet
from app.common.schemas.skill_export import (
    SkillCatalogBuiltinItem,
    SkillCatalogRecipeItem,
    SkillCatalogResponse,
    SkillExportFile,
    SkillExportMeta,
    SkillExportResponse,
)
from app.core.logging import get_logger
from app.infrastructure.persistence.models.recipe import Recipe
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM

if TYPE_CHECKING:
    from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM

logger = get_logger(__name__)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def recipe_slug(name: str) -> str:
    """Derive a filesystem-safe slug from a recipe display name."""

    base = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return (base[:80] or "skill")


def _front_matter(meta: dict[str, Any]) -> str:
    """Render YAML-like front matter without external dependencies."""

    lines = ["---"]
    for key, value in meta.items():
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, list):
            inner = ", ".join(str(v) for v in value)
            lines.append(f"{key}: [{inner}]")
        elif value is None:
            lines.append(f"{key}: null")
        else:
            escaped = str(value).replace('"', '\\"')
            lines.append(f'{key}: "{escaped}"')
    lines.append("---")
    return "\n".join(lines)


def _extract_guardrails(template: dict[str, Any]) -> list[str]:
    """Collect guardrail dicts/strings from workflow steps."""

    guardrails: list[str] = []
    steps = template.get("steps")
    if not isinstance(steps, list):
        return guardrails
    for step in steps:
        if not isinstance(step, dict):
            continue
        raw = step.get("guardrails")
        if isinstance(raw, dict):
            for k, v in raw.items():
                guardrails.append(f"{k}: {v}")
        elif isinstance(raw, str) and raw.strip():
            guardrails.append(raw.strip())
    return guardrails


def _build_tasks_prompt_md(recipe: Recipe) -> str:
    """Generate tasks.prompt.md from workflow template steps."""

    template = recipe.workflow_template or {}
    steps = template.get("steps")
    lines = [
        f"# Tasks — {recipe.name}",
        "",
        "Execute in order. Stop if verification gates fail.",
        "",
    ]
    if not isinstance(steps, list) or not steps:
        lines.append("1. Run the verified workflow steps recorded in SKILL.md.")
        return "\n".join(lines)

    for idx, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            continue
        title = (
            str(step.get("description") or "").strip()
            or str(step.get("title") or "").strip()
            or str(step.get("name") or "").strip()
            or f"Step {idx}"
        )
        role = str(step.get("agent_role") or step.get("role") or "").strip()
        lines.append(f"## {idx}. {title}")
        if role:
            lines.append(f"- Role: `{role}`")
        criteria = step.get("evaluation_criteria")
        if isinstance(criteria, dict) and criteria:
            lines.append("- Evaluation:")
            for ck, cv in criteria.items():
                lines.append(f"  - {ck}: {cv}")
        elif isinstance(criteria, str) and criteria.strip():
            lines.append(f"- Evaluation: {criteria.strip()}")
        guard = step.get("guardrails")
        if isinstance(guard, dict) and guard:
            lines.append("- Guardrails:")
            for gk, gv in guard.items():
                lines.append(f"  - {gk}: {gv}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_skill_md(recipe: Recipe) -> str:
    """Render SKILL.md compatible with supervisor SkillLibrary front matter."""

    slug = recipe_slug(recipe.name)
    total = recipe.success_count + recipe.fail_count
    success_rate = float(recipe.success_count / total) if total else 0.0
    tags = list(recipe.topic_tags or [])
    roles = _infer_roles(recipe.workflow_template)
    guardrails = _extract_guardrails(recipe.workflow_template)

    fm = _front_matter(
        {
            "version": "1.0.0",
            "priority": 70 if recipe.verified_at else 40,
            "roles": roles,
            "keywords": tags[:12],
            "source": "queenswarm.love",
            "verified": recipe.verified_at is not None,
            "verified_at": recipe.verified_at.isoformat() if recipe.verified_at else None,
            "pollen_avg": round(recipe.avg_pollen_earned, 2),
            "success_rate": round(success_rate, 4),
            "slug": slug,
        },
    )

    body_lines = [
        f"# {recipe.name}",
        "",
        (recipe.description or "Verified Queenswarm workflow skill.").strip(),
        "",
        "## Purpose",
        "",
        "Apply this recipe when the task matches the workflow below. Require simulation verification before operator-facing output.",
        "",
        "## Workflow steps",
        "",
    ]
    step_labels = _step_lines(recipe.workflow_template)
    if step_labels:
        body_lines.extend(step_labels)
    else:
        body_lines.append("1. Follow the workflow template stored in the Recipe Library.")

    body_lines.extend(["", "## Guardrails", ""])
    if guardrails:
        body_lines.extend(f"- {g}" for g in guardrails)
    else:
        body_lines.extend(
            [
                "- Never skip simulation audit for high-impact outputs.",
                "- Respect CostGovernor token budgets.",
                "- Emit pollen only after verified completion.",
            ],
        )

    body_lines.extend(
        [
            "",
            "## Verification gates",
            "",
            "1) Risks",
            "2) Unknowns",
            "3) Mitigations",
            "4) Verification evidence (simulator confidence ≥ hive threshold)",
            "",
        ],
    )
    return f"{fm}\n\n" + "\n".join(body_lines)


def _step_lines(template: dict[str, Any]) -> list[str]:
    """Numbered markdown lines for workflow steps."""

    steps = template.get("steps")
    if not isinstance(steps, list):
        return []
    lines: list[str] = []
    for idx, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            continue
        label = (
            str(step.get("description") or "").strip()
            or str(step.get("title") or "").strip()
            or str(step.get("name") or "").strip()
            or f"Step {idx}"
        )
        lines.append(f"{idx}. {label}")
    return lines


def _infer_roles(template: dict[str, Any]) -> list[str]:
    """Map workflow agent roles to supervisor skill role hints."""

    steps = template.get("steps")
    if not isinstance(steps, list):
        return ["researcher", "coder"]
    roles: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        raw = str(step.get("agent_role") or step.get("role") or "").strip().lower()
        if raw and raw not in roles:
            roles.append(raw)
    return roles[:8] or ["researcher", "coder"]


def build_export_bundle(recipe: Recipe) -> SkillExportResponse:
    """Assemble a full export bundle for one recipe row."""

    slug = recipe_slug(recipe.name)
    folder = slug
    total = recipe.success_count + recipe.fail_count
    success_rate = float(recipe.success_count / total) if total else 0.0

    skill_md = build_skill_md(recipe)
    hive_md = generate_recipe_hive_md(recipe)
    tasks_md = _build_tasks_prompt_md(recipe)
    meta_dict = meta_json_preview(recipe)
    meta_json = json.dumps(meta_dict, indent=2, sort_keys=True)
    install_command = f"npx skills@latest add queenswarm/{slug}"
    readme_md = build_readme_md(recipe=recipe, slug=slug, install_command=install_command)
    listing_md = build_listing_md(recipe=recipe, slug=slug, price_cents=resolve_skill_price_cents(recipe))
    publish = build_publish_guide(recipe=recipe, slug=slug, install_command=install_command)

    files = [
        SkillExportFile(path=f"{folder}/SKILL.md", content=skill_md),
        SkillExportFile(path=f"{folder}/HIVE.md", content=hive_md),
        SkillExportFile(path=f"{folder}/tasks.prompt.md", content=tasks_md),
        SkillExportFile(path=f"{folder}/meta.json", content=meta_json + "\n"),
        SkillExportFile(path=f"{folder}/README.md", content=readme_md),
        SkillExportFile(path=f"{folder}/LISTING.md", content=listing_md),
    ]

    meta = SkillExportMeta(
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        slug=slug,
        verified=recipe.verified_at is not None,
        verified_at=recipe.verified_at,
        success_rate=success_rate,
        avg_pollen_earned=float(recipe.avg_pollen_earned or 0.0),
        success_count=int(recipe.success_count or 0),
        fail_count=int(recipe.fail_count or 0),
        topic_tags=list(recipe.topic_tags or []),
    )

    install_hint = (
        "Sell anywhere: push to GitHub, Gumroad, or Cursor skills folder. "
        f"Bundle includes README.md + LISTING.md. In-app checkout is optional — {install_command}"
    )

    logger.info(
        "skill_export.bundle_built",
        agent_id="skill_export",
        swarm_id="recipe_library",
        task_id=str(recipe.id),
        slug=slug,
        verified=meta.verified,
        file_count=len(files),
    )

    return SkillExportResponse(
        meta=meta,
        files=files,
        install_command=install_command,
        install_hint=install_hint,
        publish=publish,
    )


def _builtin_skill_summary(snippet: SkillSnippet) -> str:
    """First descriptive line from skill body for marketplace cards."""

    for line in snippet.body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return stripped[:280]
    roles = ", ".join(snippet.roles or []) or "supervisor lanes"
    return f"Built-in hive skill loaded by {roles}."


def _builtin_skill_agent_usage(snippet: SkillSnippet) -> str:
    """Operator-facing copy for how bees apply this skill shard."""

    roles = ", ".join(snippet.roles or []) or "supervisor"
    keywords = ", ".join((snippet.keywords or [])[:5])
    if keywords:
        return f"Queen and {roles} bees inject this shard when tasks match: {keywords}."
    return f"Supervisor SkillLibrary loads `{snippet.slug}` for {roles} during planning and execution."


async def build_skills_catalog(
    session: AsyncSession,
    *,
    recipe_limit: int = 80,
    tenant_id: uuid.UUID | None = None,
) -> SkillCatalogResponse:
    """List built-in hive skills plus verified recipes eligible for export."""

    library = SkillLibrary()
    builtin: list[SkillCatalogBuiltinItem] = []
    for path in sorted(library.skills_dir.glob("*.md")):
        slug = path.stem.strip().lower()
        snippet = library.load(slug)
        if snippet is None:
            continue
        builtin.append(
            SkillCatalogBuiltinItem(
                slug=snippet.slug,
                title=snippet.title,
                version=snippet.version,
                roles=list(snippet.roles or []),
                keywords=list(snippet.keywords or []),
                summary=_builtin_skill_summary(snippet),
                agent_usage=_builtin_skill_agent_usage(snippet),
            ),
        )

    rows = await list_recipe_catalog_rows(
        session,
        verified_only=True,
        include_deprecated=False,
        needle=None,
        limit=recipe_limit,
    )
    from app.application.services.skill_access import tenant_has_skill_access
    from app.application.services.skill_marketplace_ugc import load_approved_listings_map

    recipe_ids = [row.id for row in rows]
    ugc_map = await load_approved_listings_map(session, recipe_ids)

    recipes: list[SkillCatalogRecipeItem] = []
    for row in rows:
        total = row.success_count + row.fail_count
        sr = float(row.success_count / total) if total else 0.0
        premium = is_premium_recipe(row)
        unlocked = True
        if tenant_id is not None:
            unlocked = await tenant_has_skill_access(session, tenant_id=tenant_id, recipe=row)
        listing = ugc_map.get(row.id)
        price_cents = listing.price_eur_cents if listing is not None else (resolve_skill_price_cents(row) if premium else 0)
        recipes.append(
            SkillCatalogRecipeItem(
                id=row.id,
                name=row.name,
                slug=recipe_slug(row.name),
                description=row.description,
                verified_at=row.verified_at,
                topic_tags=list(row.topic_tags or []),
                success_rate=sr,
                avg_pollen_earned=float(row.avg_pollen_earned or 0.0),
                premium=premium,
                price_eur_cents=price_cents,
                unlocked=unlocked,
                ugc=listing is not None,
                platform_cut_bps=listing.platform_cut_bps if listing is not None else None,
            ),
        )

    return SkillCatalogResponse(builtin=builtin, recipes=recipes)


async def export_recipe_skill(
    session: AsyncSession,
    recipe_id: uuid.UUID,
) -> SkillExportResponse | None:
    """Load a recipe and build its export bundle."""

    row = await session.get(Recipe, recipe_id)
    if row is None:
        return None
    return build_export_bundle(row)


def build_export_bundle_from_tenant_skill(
    skill: TenantSkillORM,
    *,
    opportunity: SkillOpportunityORM | None = None,
    forge_quality: dict[str, Any] | None = None,
) -> SkillExportResponse:
    """Assemble GitHub-ready export bundle from a tenant Skill Factory row."""

    from app.application.services.skill_factory_export_harness import (
        build_eval_report_md,
        build_harness_md,
        build_mcp_setup_md,
        build_tools_json,
    )
    from app.application.services.skill_factory_listing import (
        build_factory_listing_md,
        listing_context_from_skill_and_opportunity,
    )

    slug = skill.slug
    folder = slug
    install_command = f"npx skills@latest add queenswarm/{slug}"
    listing_ctx = listing_context_from_skill_and_opportunity(skill, opportunity)

    class _RecipeShim:
        """Minimal recipe-like object for publish asset builders."""

        id = skill.id
        name = skill.title
        description = skill.description
        topic_tags = list(skill.keywords or [])
        success_count = 1
        fail_count = 0
        avg_pollen_earned = 0.0
        verified_at = skill.verified_at
        workflow_template: dict[str, Any] = {"steps": []}

    shim = _RecipeShim()
    skill_md = skill.markdown_body.strip() or build_skill_md(shim)  # type: ignore[arg-type]
    hive_md = f"# Hive context — {skill.title}\n\n{skill.description}\n"
    tasks_md = f"# Tasks — {skill.title}\n\nFollow SKILL.md workflow in order.\n"
    meta_json = json.dumps(
        {
            "slug": slug,
            "version": skill.version,
            "source": skill.source,
            "roles": list(skill.roles or []),
            "keywords": list(skill.keywords or []),
            "export_version": "2.0",
            "harness_artifacts": ["HARNESS.md", "EVAL_REPORT.md", "TOOLS.json"],
            "price_eur_cents": listing_ctx.price_cents,
            "niche": listing_ctx.niche,
        },
        indent=2,
        sort_keys=True,
    )
    readme_md = build_readme_md(recipe=shim, slug=slug, install_command=install_command)  # type: ignore[arg-type]
    listing_md = build_factory_listing_md(skill=skill, slug=slug, ctx=listing_ctx)
    publish = build_publish_guide(recipe=shim, slug=slug, install_command=install_command)  # type: ignore[arg-type]
    harness_md = build_harness_md(skill, opportunity=opportunity)
    eval_md = build_eval_report_md(skill, forge_quality=forge_quality)
    tools_json = build_tools_json(skill, opportunity=opportunity)
    mcp_setup_md = build_mcp_setup_md(skill, opportunity=opportunity)

    files = [
        SkillExportFile(path=f"{folder}/SKILL.md", content=skill_md),
        SkillExportFile(path=f"{folder}/HARNESS.md", content=harness_md),
        SkillExportFile(path=f"{folder}/EVAL_REPORT.md", content=eval_md),
        SkillExportFile(path=f"{folder}/TOOLS.json", content=tools_json),
        SkillExportFile(path=f"{folder}/MCP_SETUP.md", content=mcp_setup_md),
        SkillExportFile(path=f"{folder}/HIVE.md", content=hive_md),
        SkillExportFile(path=f"{folder}/tasks.prompt.md", content=tasks_md),
        SkillExportFile(path=f"{folder}/meta.json", content=meta_json + "\n"),
        SkillExportFile(path=f"{folder}/README.md", content=readme_md),
        SkillExportFile(path=f"{folder}/LISTING.md", content=listing_md),
    ]

    meta = SkillExportMeta(
        recipe_id=skill.id,
        recipe_name=skill.title,
        slug=slug,
        verified=skill.verified_at is not None,
        verified_at=skill.verified_at,
        success_rate=1.0 if skill.verified_at else 0.0,
        avg_pollen_earned=0.0,
        success_count=1 if skill.verified_at else 0,
        fail_count=0,
        topic_tags=list(skill.keywords or []),
    )

    return SkillExportResponse(
        meta=meta,
        files=files,
        install_command=install_command,
        install_hint="Push folder to GitHub or Gumroad — HARNESS.md + EVAL_REPORT.md + TOOLS.json included.",
        publish=publish,
    )


__all__ = [
    "build_export_bundle",
    "build_export_bundle_from_tenant_skill",
    "build_skill_md",
    "build_skills_catalog",
    "export_recipe_skill",
    "recipe_slug",
]
