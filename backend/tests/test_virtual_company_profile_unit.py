"""Unit tests for Virtual Company operator profile."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.virtual_company_profile import (
    VirtualCompanyProfilePatch,
    merge_profile_patch,
    profile_context_block,
    profile_from_tenant,
)


def test_profile_from_tenant_empty() -> None:
    tenant = MagicMock()
    tenant.operator_settings = {}
    profile = profile_from_tenant(tenant)
    assert profile.onboarded is False
    assert profile.brand_name == ""


def test_merge_profile_patch_and_onboarded() -> None:
    merged = merge_profile_patch(
        {},
        VirtualCompanyProfilePatch(
            brand_name="Acme",
            industry="SaaS",
            primary_goal="Grow organic traffic",
            focus_areas=["marketing", "product"],
            risk_tolerance="low",
        ).model_dump(exclude_unset=True),
    )
    tenant = MagicMock()
    tenant.operator_settings = merged
    profile = profile_from_tenant(tenant)
    assert profile.onboarded is True
    assert profile.focus_areas == ["marketing", "product"]
    assert "Acme" in profile_context_block(profile)


@pytest.mark.asyncio
async def test_seed_default_operator_profile_idempotent() -> None:
    from app.application.services.virtual_company_profile import seed_default_operator_profile

    tenant = MagicMock()
    tenant.operator_settings = {}
    profile, changed = seed_default_operator_profile(tenant)
    assert changed is True
    assert profile.onboarded is True
    assert profile.brand_name == "Queenswarm Solo"

    profile2, changed2 = seed_default_operator_profile(tenant)
    assert changed2 is False
    assert profile2.brand_name == profile.brand_name


@pytest.mark.asyncio
async def test_install_free_connectors_calls_marketplace(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services import virtual_company_profile as mod

    calls: list[str] = []

    async def _fake_install(
        _session: object,
        *,
        dashboard_user_id: object,
        source: str,
        entry_id: str,
        slug_override: str | None = None,
        display_name_override: str | None = None,
    ) -> tuple[str, object | None]:
        _ = dashboard_user_id, slug_override, display_name_override
        calls.append(entry_id)
        return "installed", None

    monkeypatch.setattr(mod, "install_marketplace_entry", _fake_install)
    results = await mod.install_free_connectors(AsyncMock(), dashboard_user_id=uuid.uuid4())
    assert len(results) == 3
    assert "notion_workspace" in calls
    assert "gmail_google_workspace" in calls
    assert "github_rest" in calls


@pytest.mark.asyncio
async def test_first_run_playbook_marketing() -> None:
    from app.application.services.virtual_company_profile import first_run_playbook

    row = first_run_playbook("marketing-ops")
    assert row is not None
    assert "simulate" in row["goal"].lower()
    assert "execution-studio" in row["skills"]


def test_oauth_progress_shape() -> None:
    from app.application.services.virtual_company_profile import build_oauth_progress

    progress = build_oauth_progress(
        connectors=[
            {"slug": "notion_workspace", "installed": True, "installed_active": False},
            {"slug": "gmail_workspace", "installed": True, "installed_active": False},
        ],
        oauth_env={"notion_workspace": True, "google_gmail": False, "github_rest": False},
    )
    assert progress["configured"] == 1
    assert progress["connected"] == 0
    assert progress["total"] == 3


def test_first_run_playbooks_count() -> None:
    from app.application.services.virtual_company_profile import FIRST_RUN_PLAYBOOKS

    assert len(FIRST_RUN_PLAYBOOKS) == 7
    assert "finance-ops" in FIRST_RUN_PLAYBOOKS
    assert "product-ship" in FIRST_RUN_PLAYBOOKS


def test_oauth_setup_guide_shape() -> None:
    from app.application.services.virtual_company_profile import build_oauth_setup_guide

    guide = build_oauth_setup_guide()
    assert "redirect_uri" in guide
    assert len(guide["vendors"]) == 3
    assert guide["all_configured"] is False


@pytest.mark.asyncio
async def test_start_first_run_session_unknown_template() -> None:
    from app.application.services.virtual_company_profile import start_first_run_session

    with pytest.raises(KeyError):
        await start_first_run_session(
            AsyncMock(),
            tenant_id=uuid.uuid4(),
            template_id="unknown",
            created_by_subject="op",
        )


@pytest.mark.asyncio
async def test_build_bootstrap_checklist_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services import virtual_company_profile as mod

    tenant = MagicMock()
    tenant.id = uuid.uuid4()
    tenant.operator_settings = merge_profile_patch(
        {},
        {"brand_name": "X", "industry": "Y", "primary_goal": "Z"},
    )

    async def _routing(*_a: object, **_k: object) -> dict[str, object]:
        return {"routing_mode": "quality", "feature_enabled": True}

    async def _built(*_a: object, **_k: object) -> list[str]:
        return []

    async def _first_run(*_a: object, **_k: object) -> dict[str, object]:
        return {
            "marketing_ops_completed": False,
            "core_first_runs_completed": False,
            "all_department_first_runs_completed": False,
            "completed_count": 0,
            "playbooks_total": 6,
            "completed_templates": [],
            "sessions": [],
        }

    class _Row:
        is_builtin = False
        is_active = True
        slug = "notion_workspace"

    svc = MagicMock()
    svc.list_visible = AsyncMock(return_value=[_Row()])

    monkeypatch.setattr(mod, "load_routing_config", _routing)
    monkeypatch.setattr(mod, "DynamicConnectorService", lambda: svc)
    monkeypatch.setattr(mod, "build_first_run_status", _first_run)
    import app.application.services.virtual_company_swarm_builder as builder_mod

    monkeypatch.setattr(builder_mod, "list_built_wizard_templates", _built)

    payload = await mod.build_bootstrap_checklist(
        AsyncMock(),
        tenant=tenant,
        dashboard_user_id=uuid.uuid4(),
    )
    assert payload["profile_complete"] is True
    assert payload["departments_total"] == 6
    assert isinstance(payload["next_steps"], list)
