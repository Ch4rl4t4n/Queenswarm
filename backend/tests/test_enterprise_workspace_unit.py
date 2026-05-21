"""Tests for enterprise workspace white-label and compliance config."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.application.services.enterprise_workspace import (
    build_ha_profile_status,
    get_compliance_config,
    get_white_label_config,
    merge_enterprise_workspace_patch,
    serialize_tenant_branding_brief,
)


def _tenant(**kwargs: object) -> SimpleNamespace:
    base = {
        "id": uuid.uuid4(),
        "name": "Acme Hive",
        "slug": "acme",
        "operator_settings": {},
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_get_white_label_defaults() -> None:
    cfg = get_white_label_config(_tenant())
    assert cfg["accent_hex"] == "#FFB800"
    assert cfg["hide_platform_branding"] is False
    assert cfg["custom_domain_status"] == "pending"


def test_merge_white_label_patch() -> None:
    tenant = _tenant()
    root = merge_enterprise_workspace_patch(
        tenant,
        white_label={
            "brand_name": " Acme ",
            "accent_hex": "#00FFFF",
            "hide_platform_branding": True,
            "custom_domain": "hive.acme.com",
        },
    )
    tenant.operator_settings = root
    cfg = get_white_label_config(tenant)
    assert cfg["brand_name"] == "Acme"
    assert cfg["accent_hex"] == "#00FFFF"
    assert cfg["hide_platform_branding"] is True
    assert cfg["custom_domain"] == "hive.acme.com"


def test_merge_compliance_patch_clamps_retention() -> None:
    tenant = _tenant(
        operator_settings={"enterprise_compliance": {"data_retention_days": 99999}},
    )
    cfg = get_compliance_config(tenant)
    assert cfg["data_retention_days"] == 2555


def test_build_ha_profile_status_shape() -> None:
    profile = build_ha_profile_status()
    assert "readiness_pct" in profile
    assert "profile_label" in profile
    assert 0 <= profile["readiness_pct"] <= 100
    from app.common.schemas.enterprise_workspace import HaProfileStatus

    HaProfileStatus.model_validate(profile)


def test_serialize_tenant_branding_brief_when_empty() -> None:
    assert serialize_tenant_branding_brief(_tenant()) is None


def test_serialize_tenant_branding_brief_when_brand_set() -> None:
    tenant = _tenant(
        operator_settings={"white_label": {"brand_name": "Acme", "accent_hex": "#00FFFF"}},
    )
    brief = serialize_tenant_branding_brief(tenant)
    assert brief is not None
    assert brief["brand_name"] == "Acme"
    assert brief["accent_hex"] == "#00FFFF"
