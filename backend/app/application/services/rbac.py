"""Role-based access control helpers for tenant-scoped dashboard surfaces."""

from __future__ import annotations

from typing import Final

ROLE_OWNER: Final[str] = "owner"
ROLE_ADMIN: Final[str] = "admin"
ROLE_MEMBER: Final[str] = "member"
ROLE_VIEWER: Final[str] = "viewer"
ROLE_GUEST: Final[str] = "guest"

VALID_TENANT_ROLES: Final[set[str]] = {ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER, ROLE_VIEWER, ROLE_GUEST}

_ROLE_PERMISSIONS: Final[dict[str, set[str]]] = {
    ROLE_OWNER: {"*"},
    ROLE_ADMIN: {
        "supervisor:view",
        "supervisor:run",
        "costs:view",
        "connectors:view",
        "connectors:edit",
        "team:view",
        "team:manage",
        "resources:share",
        "settings:view",
    },
    ROLE_MEMBER: {
        "supervisor:view",
        "supervisor:run",
        "connectors:view",
        "connectors:edit",
        "team:view",
        "resources:share",
        "settings:view",
    },
    ROLE_VIEWER: {
        "supervisor:view",
        "connectors:view",
        "costs:view",
        "team:view",
        "settings:view",
    },
    ROLE_GUEST: {
        "supervisor:view",
        "settings:view",
    },
}


def normalize_tenant_role(raw: str | None) -> str:
    """Normalize role and fallback safely to guest when unknown."""

    role = (raw or "").strip().lower()
    if role in VALID_TENANT_ROLES:
        return role
    return ROLE_GUEST


def permissions_for_role(role: str | None) -> set[str]:
    """Resolve effective permissions set for one role."""

    return set(_ROLE_PERMISSIONS.get(normalize_tenant_role(role), _ROLE_PERMISSIONS[ROLE_GUEST]))


def has_permission(*, role: str | None, permission: str) -> bool:
    """Return True when role grants requested permission."""

    perms = permissions_for_role(role)
    req = permission.strip().lower()
    if "*" in perms:
        return True
    if req in perms:
        return True
    wildcard = f"{req.split(':', 1)[0]}:*" if ":" in req else f"{req}:*"
    return wildcard in perms


__all__ = [
    "ROLE_ADMIN",
    "ROLE_GUEST",
    "ROLE_MEMBER",
    "ROLE_OWNER",
    "ROLE_VIEWER",
    "VALID_TENANT_ROLES",
    "has_permission",
    "normalize_tenant_role",
    "permissions_for_role",
]
