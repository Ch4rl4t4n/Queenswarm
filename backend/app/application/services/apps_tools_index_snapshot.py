"""Compose unified Apps & Tools index snapshot for frontend."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.application.services.capability_registry import (
    CapabilityContractOut,
    CapabilityWorkspaceOut,
    compose_capability_registry_snapshot,
)
from app.application.services.module_policy_packs import (
    ModulePolicyPackOut,
    compose_module_policy_pack_snapshot,
)


class AppsToolsIndexSnapshotOut(BaseModel):
    """Unified payload for Apps & Tools module index pages."""

    model_config = ConfigDict(extra="ignore")

    generated_at: datetime
    version: str = "v1"
    workspaces: list[CapabilityWorkspaceOut] = Field(default_factory=list)
    capabilities: list[CapabilityContractOut] = Field(default_factory=list)
    policies: list[ModulePolicyPackOut] = Field(default_factory=list)


def compose_apps_tools_index_snapshot(*, include_disabled: bool = False) -> AppsToolsIndexSnapshotOut:
    """Return Apps & Tools-only capability + policy snapshot for index UI."""

    capability_snapshot = compose_capability_registry_snapshot(include_disabled=include_disabled)
    policy_snapshot = compose_module_policy_pack_snapshot(include_disabled=include_disabled)

    workspaces = [row for row in capability_snapshot.workspaces if row.layer == "apps_tools"]
    module_keys = {row.module_key for row in workspaces}
    capabilities = [row for row in capability_snapshot.capabilities if row.owner_module in module_keys]
    policies = [row for row in policy_snapshot.modules if row.module_key in module_keys]

    return AppsToolsIndexSnapshotOut(
        generated_at=datetime.now(tz=UTC),
        workspaces=workspaces,
        capabilities=capabilities,
        policies=policies,
    )


__all__ = ["AppsToolsIndexSnapshotOut", "compose_apps_tools_index_snapshot"]
