from __future__ import annotations

from app.application.services.rbac import has_permission, normalize_tenant_role, permissions_for_role


def test_normalize_tenant_role_when_unknown_then_guest() -> None:
    assert normalize_tenant_role("mystery") == "guest"
    assert normalize_tenant_role(None) == "guest"


def test_permissions_for_role_when_owner_then_has_global_wildcard() -> None:
    perms = permissions_for_role("owner")
    assert "*" in perms


def test_has_permission_when_member_then_can_run_supervisor_not_costs() -> None:
    assert has_permission(role="member", permission="supervisor:run") is True
    assert has_permission(role="member", permission="costs:view") is False


def test_has_permission_when_viewer_then_read_only_access() -> None:
    assert has_permission(role="viewer", permission="supervisor:view") is True
    assert has_permission(role="viewer", permission="connectors:edit") is False
