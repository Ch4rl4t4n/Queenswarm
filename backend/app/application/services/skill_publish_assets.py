"""Publish-ready assets for verified skill exports (GitHub, Gumroad, Cursor, Stripe)."""

from __future__ import annotations

from app.application.services.skill_marketplace_policy import is_premium_recipe, resolve_skill_price_cents
from app.common.schemas.skill_export import SkillPublishChannel, SkillPublishGuide
from app.core.config import settings
from app.infrastructure.persistence.models.recipe import Recipe


def _price_eur_display(cents: int) -> str:
    return f"€{(cents / 100):.2f}"


def _github_repo_url() -> str:
    org = settings.skill_publish_github_org.strip() or "queenswarm"
    repo = settings.skill_publish_github_repo.strip() or "skills"
    return f"https://github.com/{org}/{repo}"


def _app_base() -> str:
    domain = (settings.domain or "queenswarm.love").strip()
    return f"https://{domain}"


def build_readme_md(*, recipe: Recipe, slug: str, install_command: str) -> str:
    """GitHub README for a skill folder."""

    desc = (recipe.description or "Verified Queenswarm swarm skill.").strip()
    total = recipe.success_count + recipe.fail_count
    sr = (recipe.success_count / total * 100) if total else 0.0
    return "\n".join(
        [
            f"# {recipe.name}",
            "",
            desc,
            "",
            "## Install (Cursor / Claude Code)",
            "",
            "```bash",
            install_command,
            "```",
            "",
            "Or copy this folder into `.cursor/skills/` with `SKILL.md` at the root (folder name: `{slug}`).".format(
                slug=slug,
            ),
            "",
            "## Bundle contents",
            "",
            "- `SKILL.md` — agent skill definition",
            "- `HIVE.md` — hive colony context",
            "- `tasks.prompt.md` — ordered task prompts",
            "- `meta.json` — verification telemetry",
            "- `LISTING.md` — Gumroad / marketplace copy",
            "",
            "## Verification",
            "",
            f"- Source: [queenswarm.love](https://{settings.domain})",
            f"- Simulation-gated: **{'yes' if recipe.verified_at else 'pending'}**",
            f"- Success rate: **{sr:.0f}%** ({recipe.success_count}/{total} runs)",
            f"- Avg pollen: **{recipe.avg_pollen_earned:.1f}**",
            "",
            "## License",
            "",
            "See repository LICENSE. Commercial use allowed per your purchase terms.",
            "",
        ],
    )


def build_listing_md(*, recipe: Recipe, slug: str, price_cents: int) -> str:
    """Gumroad / marketplace listing copy."""

    desc = (recipe.description or "Verified agent skill from the Queenswarm hive.").strip()
    price = _price_eur_display(price_cents)
    tags = ", ".join(str(t) for t in (recipe.topic_tags or [])[:8])
    return "\n".join(
        [
            f"# Listing — {recipe.name}",
            "",
            "## Title",
            "",
            recipe.name.replace("Premium — ", "").strip(),
            "",
            "## Price suggestion",
            "",
            price,
            "",
            "## Short description (Gumroad subtitle)",
            "",
            desc[:240],
            "",
            "## Long description",
            "",
            f"{desc}",
            "",
            "Built and verified inside **Queenswarm** — a bee-hive agent swarm. Every step ran through simulation gates before export.",
            "",
            "### What you get",
            "",
            "- Cursor / Claude Code compatible `SKILL.md`",
            "- `HIVE.md` colony context + `tasks.prompt.md` runbook",
            "- Verification metadata (success rate, pollen rewards)",
            "",
            "### Install",
            "",
            f"```bash",
            f"npx skills@latest add queenswarm/{slug}",
            f"```",
            "",
            f"Tags: {tags or 'agent-skill, queenswarm'}",
            "",
            "## Cover image prompt",
            "",
            f"Neon-dark hexagonal hive card, amber glow, title \"{recipe.name[:40]}\", cyberpunk bee motif, 1280x720",
            "",
        ],
    )


def build_publish_guide(*, recipe: Recipe, slug: str, install_command: str) -> SkillPublishGuide:
    """Multi-channel publish checklist for operator UI."""

    premium = is_premium_recipe(recipe)
    price_cents = resolve_skill_price_cents(recipe) if premium else settings.skill_export_premium_price_eur_cents
    github = _github_repo_url()
    base = _app_base()
    folder = slug

    channels = [
        SkillPublishChannel(
            id="github",
            label="GitHub",
            description=f"Push `{folder}/` to {settings.skill_publish_github_org}/{settings.skill_publish_github_repo}",
            action_url=f"{github}/new",
            copy_text=(
                f"mkdir -p {folder} && cp SKILL.md HIVE.md tasks.prompt.md meta.json LISTING.md README.md {folder}/\n"
                f"git add {folder} && git commit -m \"feat: add {slug} skill\" && git push"
            ),
        ),
        SkillPublishChannel(
            id="gumroad",
            label="Gumroad",
            description="Create digital product — paste LISTING.md from bundle",
            action_url="https://gumroad.com/products/new",
            copy_text=build_listing_md(recipe=recipe, slug=slug, price_cents=price_cents),
        ),
        SkillPublishChannel(
            id="cursor",
            label="Cursor / Claude",
            description="Install locally for testing before public sale",
            action_url=None,
            copy_text=(
                f"Copy folder to ~/.cursor/skills/{slug}/ (SKILL.md required)\n\n"
                f"Or run:\n{install_command}"
            ),
        ),
        SkillPublishChannel(
            id="queenswarm",
            label="Queenswarm Stripe",
            description="Optional in-app unlock for hive operators",
            action_url=f"{base}/integrations?tab=skills",
            copy_text=None,
        ),
    ]

    checklist = [
        "Run swarm mission in Ballroom → verify recipe in Recipe Library",
        "Export bundle → test SKILL.md in Cursor",
        f"Create GitHub folder `{folder}/` and push README + skill files",
        "Publish Gumroad listing (paste LISTING.md) or sell on GitHub Sponsors",
        "Optional: tag recipe `premium` / `premium-9` for Stripe unlock on queenswarm.love",
        "Share install command: npx skills add queenswarm/{slug}",
    ]

    return SkillPublishGuide(
        slug=slug,
        suggested_price_eur_cents=price_cents,
        suggested_price_display=_price_eur_display(price_cents),
        github_repo_url=github,
        github_folder_path=folder,
        gumroad_new_product_url="https://gumroad.com/products/new",
        ballroom_mission_hint="Ballroom → Product Mission — run niche → produce → package → listing",
        install_command=install_command,
        channels=channels,
        checklist=checklist,
    )


__all__ = ["build_listing_md", "build_publish_guide", "build_readme_md"]
