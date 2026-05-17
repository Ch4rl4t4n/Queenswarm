"""Static metadata for Ballroom dynamic manager lanes (Phase 0.5 hierarchy)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.infrastructure.persistence.models.enums import AgentRole


@dataclass(frozen=True, slots=True)
class ManagerTemplateSpec:
    """One of six seeded manager personas — routed through Recipe Library excerpts + Ballroom."""

    slug: str
    display_name: str
    connector_allowlist: tuple[str, ...]
    sub_swarm_roles: tuple[AgentRole, ...]
    prompt_rel_path: str

    def prompt_text(self) -> str:
        """Load markdown prompt bundled next to runtime code."""

        base = Path(__file__).resolve().parent
        path = base / self.prompt_rel_path
        return path.read_text(encoding="utf-8").strip()

    def __repr__(self) -> str:
        """Compact identity for swarm logs."""

        return f"ManagerTemplateSpec(slug={self.slug!r})"


__all__ = ["ManagerTemplateSpec"]
