"""Dynamic sub-agent spawn policy using existing manager/specialist extension points."""

from __future__ import annotations

from app.domain.agents.factory import specialist_roles_for_manager_lane
from app.domain.agents.managers.registry import list_manager_slugs
from app.infrastructure.persistence.models.enums import AgentRole

ROLE_TO_MANAGER_SLUG: dict[str, str] = {
    "researcher": "research_intelligence",
    "coder": "execution_operations",
    "browser_operator": "execution_operations",
    "critic": "review_quality",
    "designer": "content_creation",
}


def infer_manager_slug_for_role(role: str) -> str:
    """Map dashboard role slugs onto existing manager template lanes."""

    key = role.strip().lower()
    fallback = "execution_operations"
    allowed = set(list_manager_slugs())
    candidate = ROLE_TO_MANAGER_SLUG.get(key, fallback)
    return candidate if candidate in allowed else fallback


def infer_specialist_roles_for_role(role: str) -> list[str]:
    """Surface specialist role names for a dashboard sub-agent role."""

    manager_slug = infer_manager_slug_for_role(role)
    roles = specialist_roles_for_manager_lane(manager_slug)
    return [r.value if isinstance(r, AgentRole) else str(r) for r in roles]

