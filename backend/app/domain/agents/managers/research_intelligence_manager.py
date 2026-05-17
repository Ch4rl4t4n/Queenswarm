"""Research & Intelligence manager lane — Ballroom Phase 0.5."""

from __future__ import annotations

from app.domain.agents.managers.registry import get_manager_template


class ResearchIntelligenceManager:
    """Grounded scouting / intel coordination persona."""

    slug: str = "research_intelligence"

    @classmethod
    def lane_title(cls) -> str:
        """Human label for Ballroom transcripts."""

        return get_manager_template(cls.slug).display_name


__all__ = ["ResearchIntelligenceManager"]
