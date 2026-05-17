"""Structured Recipe Library payloads for Ballroom manager personas (Phase 0.5)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.domain.agents.managers.registry import get_manager_template


def manager_lane_workflow_stub(*, slug: str) -> dict[str, Any]:
    """Minimal JSON scaffold tagged for semantic recall + imitation plumbing."""

    spec = get_manager_template(slug)
    return {
        "kind": "ballroom_manager_lane",
        "revision": "phase0.5",
        "lane_slug": spec.slug,
        "display_name": spec.display_name,
        "connector_allowlist": list(spec.connector_allowlist),
        "recommended_roles": [role.value for role in spec.sub_swarm_roles],
        "notes": (
            "Auto-seeded Ballroom lane blueprint — enrich with breaker steps + connector policies in Phase 1."
        ),
    }


class BallroomPostMortemOutline(BaseModel):
    """Lite JSON shape produced by orchestrator-directed reflection."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    summary_markdown: str
    pollen_learnings: str = ""
    next_time_checklist: str = ""

    def as_workflow_bundle(
        self,
        *,
        mission_id: str,
        preview_digest: str,
        lane_slugs: list[str],
    ) -> dict[str, Any]:
        """Merge textual reflection with deterministic lane bookkeeping."""

        return {
            "kind": "ballroom_post_mortem",
            "revision": "phase0.5",
            "mission_id": mission_id,
            "manager_template_slugs": list(lane_slugs),
            "breaker_digest": preview_digest.strip()[:4000],
            "post_mortem": self.summary_markdown.strip()[:12_000],
            "pollen_learnings": self.pollen_learnings.strip()[:2000],
            "next_time_checklist": self.next_time_checklist.strip()[:2000],
        }


__all__ = ["BallroomPostMortemOutline", "manager_lane_workflow_stub"]
