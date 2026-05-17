"""Review & Quality manager lane — Ballroom Phase 0.5."""

from __future__ import annotations

from app.domain.agents.managers.registry import get_manager_template


class ReviewQualityManager:
    """Verification rubric persona shared with orchestrator post-mortems."""

    slug: str = "review_quality"

    @classmethod
    def lane_title(cls) -> str:
        return get_manager_template(cls.slug).display_name


__all__ = ["ReviewQualityManager"]
