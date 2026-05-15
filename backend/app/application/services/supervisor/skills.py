"""Lightweight Markdown skill loader for supervisor + sub-agent prompts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_ROLE_SKILLS: dict[str, list[str]] = {
    "researcher": ["context", "diagnose"],
    "coder": ["tdd", "decide"],
    "browser_operator": ["context", "decide"],
    "critic": ["grill-me", "diagnose"],
    "designer": ["context", "decide"],
}


@dataclass(slots=True)
class SkillSnippet:
    """One parsed Markdown skill document."""

    slug: str
    title: str
    body: str


class SkillLibrary:
    """Reads Markdown skills from ``backend/app/skills`` with lazy in-memory cache."""

    def __init__(self, skills_dir: Path | None = None) -> None:
        base = skills_dir or (Path(__file__).resolve().parents[3] / "skills")
        self._skills_dir = base
        self._cache: dict[str, SkillSnippet] = {}

    @property
    def skills_dir(self) -> Path:
        """Return the resolved skills directory path."""

        return self._skills_dir

    def load(self, slug: str) -> SkillSnippet | None:
        """Load one skill by slug (without ``.md`` suffix)."""

        key = slug.strip().lower()
        if not key:
            return None
        if key in self._cache:
            return self._cache[key]
        path = self._skills_dir / f"{key}.md"
        if not path.exists() or not path.is_file():
            return None
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return None
        first = raw.splitlines()[0].strip()
        title = first.removeprefix("#").strip() if first.startswith("#") else key
        parsed = SkillSnippet(slug=key, title=title or key, body=raw)
        self._cache[key] = parsed
        return parsed

    def resolve_slugs(self, *, role: str, requested: list[str] | None = None) -> list[str]:
        """Return deduplicated valid slugs for a role and optional explicit request."""

        base = list(DEFAULT_ROLE_SKILLS.get(self._normalize_role(role), []))
        merged = [*(requested or []), *base]
        out: list[str] = []
        seen: set[str] = set()
        for item in merged:
            slug = item.strip().lower()
            if not slug or slug in seen:
                continue
            if self.load(slug) is None:
                continue
            seen.add(slug)
            out.append(slug)
        return out

    @staticmethod
    def _normalize_role(role: str) -> str:
        """Normalize role slug consistently across supervisor helpers."""

        return role.strip().lower().replace("-", "_")

    def build_prompt_block(self, slugs: list[str]) -> str:
        """Construct a compact prompt appendix for selected skills."""

        chunks: list[str] = []
        for slug in slugs:
            skill = self.load(slug)
            if skill is None:
                continue
            chunks.append(f"## Skill: {skill.title}\n{skill.body}")
        return "\n\n".join(chunks).strip()


__all__ = ["DEFAULT_ROLE_SKILLS", "SkillLibrary", "SkillSnippet"]
