"""Skill loader + selector for supervisor and sub-agent prompts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

DEFAULT_ROLE_SKILLS: dict[str, list[str]] = {
    "researcher": ["context", "multi-step-reasoning", "decision-frameworks"],
    "coder": ["tdd", "self-review-loop", "tool-use-orchestration"],
    "browser_operator": ["context", "tool-use-orchestration", "decision-frameworks"],
    "critic": ["grill-me", "self-review-loop", "diagnose"],
    "designer": ["context", "decision-frameworks", "self-review-loop"],
}


@dataclass(slots=True)
class SkillSnippet:
    """One parsed Markdown skill document."""

    slug: str
    title: str
    body: str
    version: str = "1.0.0"
    priority: int = 50
    roles: list[str] | None = None
    keywords: list[str] | None = None
    reference_mode: bool = False
    references: list[str] | None = None


class SkillLibrary:
    """Reads Markdown skills and dynamically selects best-fit combinations."""

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
        meta, body = self._split_front_matter(raw)
        normalized_body = body.strip()
        if not normalized_body:
            return None
        first = normalized_body.splitlines()[0].strip()
        title = first.removeprefix("#").strip() if first.startswith("#") else key
        roles = [self._normalize_role(item) for item in self._meta_list(meta.get("roles"))]
        keywords = [item.strip().lower() for item in self._meta_list(meta.get("keywords")) if item.strip()]
        reference_mode = self._meta_bool(meta.get("reference_mode"))
        references = [item.strip() for item in self._meta_list(meta.get("references")) if item.strip()]
        parsed = SkillSnippet(
            slug=key,
            title=title or key,
            body=normalized_body,
            version=str(meta.get("version") or "1.0.0").strip() or "1.0.0",
            priority=self._meta_priority(meta.get("priority")),
            roles=roles or None,
            keywords=keywords or None,
            reference_mode=reference_mode,
            references=references or None,
        )
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

    def select_for_task(
        self,
        *,
        role: str,
        goal: str,
        requested: list[str] | None = None,
        max_skills: int = 5,
    ) -> list[str]:
        """Select prioritized skills based on role defaults + goal keyword match."""

        normalized_role = self._normalize_role(role)
        goal_tokens = self._tokenize(goal)
        explicit = {
            item.strip().lower()
            for item in (requested or [])
            if isinstance(item, str) and item.strip()
        }
        baseline = self.resolve_slugs(role=normalized_role, requested=requested)
        baseline_set = set(baseline)
        candidates = set(baseline)
        for slug in self.list_available_slugs():
            skill = self.load(slug)
            if skill is None:
                continue
            if skill.roles and normalized_role not in set(skill.roles):
                continue
            if skill.keywords and goal_tokens and goal_tokens.intersection(set(skill.keywords)):
                candidates.add(slug)
            elif not skill.keywords and slug in baseline_set:
                candidates.add(slug)

        scored: list[tuple[float, str]] = []
        for slug in candidates:
            skill = self.load(slug)
            if skill is None:
                continue
            score = float(skill.priority) / 100.0
            if slug in baseline_set:
                score += 0.35
            if slug in explicit:
                score += 1.1
            if skill.roles and normalized_role in set(skill.roles):
                score += 0.2
            if skill.keywords and goal_tokens:
                overlap = len(goal_tokens.intersection(set(skill.keywords)))
                score += min(0.6, overlap * 0.15)
            scored.append((score, slug))

        scored.sort(
            key=lambda item: (
                -item[0],
                -int(self.load(item[1]).priority if self.load(item[1]) else 0),
                item[1],
            ),
        )
        out: list[str] = []
        for _score, slug in scored:
            if slug in out:
                continue
            out.append(slug)
            if len(out) >= max(1, int(max_skills)):
                break
        return out

    def skill_manifest(self, slugs: list[str]) -> list[dict[str, str | int]]:
        """Return compact version/priority metadata for selected skills."""

        out: list[dict[str, str | int]] = []
        for slug in slugs:
            item = self.load(slug)
            if item is None:
                continue
            out.append(
                {
                    "slug": item.slug,
                    "title": item.title,
                    "version": item.version,
                    "priority": item.priority,
                },
            )
        return out

    @staticmethod
    def _normalize_role(role: str) -> str:
        """Normalize role slug consistently across supervisor helpers."""

        return role.strip().lower().replace("-", "_")

    def list_available_slugs(self) -> list[str]:
        """List available skill markdown slugs."""

        if not self._skills_dir.exists():
            return []
        rows: list[str] = []
        for item in self._skills_dir.glob("*.md"):
            if item.is_file():
                rows.append(item.stem.strip().lower())
        return sorted({slug for slug in rows if slug})

    def build_prompt_block(self, slugs: list[str], *, lazy_fetch: bool = False) -> str:
        """Construct a compact prompt appendix for selected skills (sync).

        Reference-mode skills emit pointers unless ``lazy_fetch=True`` (use async variant).
        """

        chunks: list[str] = []
        for slug in slugs:
            skill = self.load(slug)
            if skill is None:
                continue
            chunks.append(self._format_skill_chunk(skill, fetched_refs=None))
        return "\n\n".join(chunks).strip()

    async def build_prompt_block_async(self, slugs: list[str], *, lazy_fetch: bool = True) -> str:
        """Build skill prompt block with optional lazy reference fetch."""

        from app.application.services.supervisor.skill_reference_fetch import fetch_skill_reference
        from app.core.config import settings

        chunks: list[str] = []
        for slug in slugs:
            skill = self.load(slug)
            if skill is None:
                continue
            fetched: list[str] | None = None
            if (
                lazy_fetch
                and settings.skill_lazy_reference_fetch_enabled
                and skill.reference_mode
                and skill.references
            ):
                fetched = []
                for ref in skill.references[:4]:
                    text = await fetch_skill_reference(
                        ref,
                        max_chars=settings.skill_reference_fetch_max_chars,
                    )
                    if text:
                        fetched.append(f"### Reference: {ref}\n{text}")
            chunks.append(self._format_skill_chunk(skill, fetched_refs=fetched))
        return "\n\n".join(chunks).strip()

    def _format_skill_chunk(self, skill: SkillSnippet, *, fetched_refs: list[str] | None) -> str:
        """Render one skill section for supervisor prompts."""

        header = f"## Skill: {skill.title} (v{skill.version}, p{skill.priority})"
        if skill.reference_mode:
            header += " [reference mode]"
        if fetched_refs:
            ref_body = "\n\n".join(fetched_refs)
            summary = skill.body[:600].strip()
            return f"{header}\n{summary}\n\n{ref_body}".strip()
        if skill.reference_mode and skill.references:
            pointers = "\n".join(f"- {ref}" for ref in skill.references[:6])
            summary = skill.body[:600].strip()
            return f"{header}\nSummary:\n{summary}\n\nFetch on demand:\n{pointers}".strip()
        return f"{header}\n{skill.body}".strip()

    @staticmethod
    def _meta_bool(raw: str | None) -> bool:
        if raw is None:
            return False
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _split_front_matter(raw: str) -> tuple[dict[str, str], str]:
        """Parse minimal YAML-like front matter block."""

        if not raw.startswith("---\n"):
            return {}, raw
        marker = "\n---\n"
        idx = raw.find(marker, 4)
        if idx == -1:
            return {}, raw
        head = raw[4:idx].strip()
        body = raw[idx + len(marker) :]
        meta: dict[str, str] = {}
        for line in head.splitlines():
            text = line.strip()
            if not text or text.startswith("#") or ":" not in text:
                continue
            key, value = text.split(":", 1)
            norm_key = key.strip().lower()
            norm_value = value.strip()
            if norm_key:
                meta[norm_key] = norm_value
        return meta, body

    @staticmethod
    def _meta_list(raw: str | None) -> list[str]:
        if raw is None:
            return []
        trimmed = raw.strip()
        if not trimmed:
            return []
        if trimmed.startswith("[") and trimmed.endswith("]"):
            trimmed = trimmed[1:-1]
        return [item.strip().strip("'").strip('"') for item in trimmed.split(",") if item.strip()]

    @staticmethod
    def _meta_priority(raw: str | None) -> int:
        if raw is None:
            return 50
        try:
            return max(0, min(100, int(raw.strip())))
        except ValueError:
            return 50

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {m.group(0).lower() for m in re.finditer(r"[a-zA-Z_]{3,}", text or "")}


__all__ = ["DEFAULT_ROLE_SKILLS", "SkillLibrary", "SkillSnippet"]
