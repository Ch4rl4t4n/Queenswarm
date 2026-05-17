"""Content & Creation manager lane — Ballroom Phase 0.5."""

from __future__ import annotations

from app.domain.agents.managers.registry import get_manager_template


class ContentCreationManager:
    """Audience-ready drafting + channel variants persona."""

    slug: str = "content_creation"

    @classmethod
    def lane_title(cls) -> str:
        return get_manager_template(cls.slug).display_name


__all__ = ["ContentCreationManager"]
