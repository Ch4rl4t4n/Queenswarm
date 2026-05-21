"""Unit tests for tenant session playbook automation config."""

from __future__ import annotations

from types import SimpleNamespace

from app.application.services.supervisor.session_playbook_config import (
    auto_save_mark_verified_on_approve,
    auto_save_playbook_on_approve_enabled,
    merge_tenant_session_playbook_patch,
    serialize_session_playbook_config_view,
)


def _tenant(**overrides: object) -> SimpleNamespace:
    base = {"operator_settings": {}}
    base.update(overrides)
    return SimpleNamespace(**base)


def test_auto_save_playbook_defaults_disabled() -> None:
    tenant = _tenant()
    assert auto_save_playbook_on_approve_enabled(tenant) is False
    assert auto_save_mark_verified_on_approve(tenant) is True


def test_merge_tenant_session_playbook_patch() -> None:
    tenant = _tenant()
    root = merge_tenant_session_playbook_patch(
        tenant,
        auto_save_on_approve=True,
        mark_verified_on_auto_save=False,
    )
    tenant.operator_settings = root
    assert auto_save_playbook_on_approve_enabled(tenant) is True
    assert auto_save_mark_verified_on_approve(tenant) is False


def test_serialize_session_playbook_config_view() -> None:
    tenant = _tenant(
        operator_settings={
            "supervisor_session_playbook": {
                "auto_save_on_approve": True,
                "mark_verified_on_auto_save": True,
            },
        },
    )
    view = serialize_session_playbook_config_view(tenant)
    assert view["auto_save_on_approve"] is True
    assert view["mark_verified_on_auto_save"] is True
