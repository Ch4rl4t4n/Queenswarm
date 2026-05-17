"""Personal & Life manager lane — Ballroom Phase 0.5."""

from __future__ import annotations

from app.domain.agents.managers.registry import get_manager_template


class PersonalLifeManager:
    """Low-friction life planning persona."""

    slug: str = "personal_life"

    @classmethod
    def lane_title(cls) -> str:
        return get_manager_template(cls.slug).display_name


__all__ = ["PersonalLifeManager"]
