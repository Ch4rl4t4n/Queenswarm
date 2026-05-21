"""HTTP contracts for white-label branding and enterprise compliance workspace."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WhiteLabelConfig(BaseModel):
    """Tenant-facing hive branding overrides."""

    model_config = ConfigDict(extra="forbid")

    brand_name: str | None = None
    logo_url: str | None = None
    accent_hex: str = Field(default="#FFB800", pattern=r"^#[0-9A-Fa-f]{6}$")
    hide_platform_branding: bool = False
    custom_domain: str | None = None
    custom_domain_status: str = Field(default="pending")


class WhiteLabelConfigPatch(BaseModel):
    """Partial white-label update."""

    model_config = ConfigDict(extra="forbid")

    brand_name: str | None = Field(default=None, max_length=64)
    logo_url: str | None = Field(default=None, max_length=512)
    accent_hex: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    hide_platform_branding: bool | None = None
    custom_domain: str | None = Field(default=None, max_length=253)


class EnterpriseComplianceConfig(BaseModel):
    """Compliance profile stored per tenant."""

    model_config = ConfigDict(extra="forbid")

    data_retention_days: int = Field(default=365, ge=30, le=2555)
    compliance_contact_email: str | None = None
    soc2_attestation_url: str | None = None
    monthly_audit_export: bool = False
    dedicated_hive_note: str | None = None


class EnterpriseCompliancePatch(BaseModel):
    """Partial compliance profile update."""

    model_config = ConfigDict(extra="forbid")

    data_retention_days: int | None = Field(default=None, ge=30, le=2555)
    compliance_contact_email: str | None = Field(default=None, max_length=320)
    soc2_attestation_url: str | None = Field(default=None, max_length=512)
    monthly_audit_export: bool | None = None
    dedicated_hive_note: str | None = Field(default=None, max_length=512)


class HaProfileStatus(BaseModel):
    """Deployment HA readiness signals (read-only)."""

    model_config = ConfigDict(extra="forbid")

    ha_mode_enabled: bool
    redis_failover_configured: bool
    postgres_replica_configured: bool
    backup_drill_script_available: bool = True
    profile_label: str
    readiness_pct: int = Field(ge=0, le=100)


class EnterpriseWorkspaceView(BaseModel):
    """Combined enterprise workspace configuration."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    tenant_name: str
    white_label: WhiteLabelConfig
    compliance: EnterpriseComplianceConfig
    ha_profile: HaProfileStatus
    custom_branding_allowed: bool


class EnterpriseWorkspacePatch(BaseModel):
    """Partial update for white-label and compliance buckets."""

    model_config = ConfigDict(extra="forbid")

    white_label: WhiteLabelConfigPatch | None = None
    compliance: EnterpriseCompliancePatch | None = None


class ComplianceExportBundle(BaseModel):
    """Tenant compliance export for auditors."""

    model_config = ConfigDict(extra="forbid")

    exported_at: str
    tenant_id: str
    tenant_name: str
    white_label: WhiteLabelConfig
    compliance: EnterpriseComplianceConfig
    ha_profile: HaProfileStatus
    audit_log_count: int
    audit_logs: list[dict[str, object]]


__all__ = [
    "ComplianceExportBundle",
    "EnterpriseComplianceConfig",
    "EnterpriseCompliancePatch",
    "EnterpriseWorkspacePatch",
    "EnterpriseWorkspaceView",
    "HaProfileStatus",
    "WhiteLabelConfig",
    "WhiteLabelConfigPatch",
]
