"""Micro-SaaS Factory — landing + auth + deploy blueprint snapshot (P3 #85)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.enterprise_workspace import get_white_label_config
from app.application.services.virtual_company_profile import profile_from_tenant
from app.core.config import settings
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService
from app.infrastructure.persistence.models.tenant import Tenant

MICRO_SAAS_BLUEPRINT: tuple[dict[str, str], ...] = (
    {
        "id": "mvp_scope",
        "label": "MVP scope",
        "detail": "One sharp job, 3–5 bees, simulate-first delivery.",
    },
    {
        "id": "landing",
        "label": "Landing page",
        "detail": "Public /magnet or /factory page → Swarm Builder CTA.",
    },
    {
        "id": "auth",
        "label": "Auth lane",
        "detail": "Dashboard JWT + tenant RBAC — extend for product users later.",
    },
    {
        "id": "monetization",
        "label": "Monetization lane",
        "detail": "Billing stack is handled outside Queenswarm runtime.",
    },
    {
        "id": "deploy",
        "label": "Deploy recipe",
        "detail": "docker compose → health check → zero-downtime switch.",
    },
)


class MicroSaasStepOut(BaseModel):
    """One factory checklist step."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    status: str
    detail: str


class MicroSaasActionOut(BaseModel):
    """Operator action row."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    detail: str
    priority: str
    href: str | None = None


class MicroSaasSnapshotOut(BaseModel):
    """Micro-SaaS factory operator snapshot."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    progress_pct: int = 0
    product_name: str = "Micro-SaaS MVP"
    deploy_domain: str = ""
    steps: list[MicroSaasStepOut] = Field(default_factory=list)
    blueprint: list[dict[str, str]] = Field(default_factory=list)
    actions: list[MicroSaasActionOut] = Field(default_factory=list)


class MicroSaasPublicBlueprintOut(BaseModel):
    """Public blueprint — no tenant secrets."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    phases: list[dict[str, str]] = Field(default_factory=list)
    stack: dict[str, str] = Field(default_factory=dict)
    disclaimer: str = ""


def build_public_micro_saas_blueprint() -> MicroSaasPublicBlueprintOut:
    """Return public Micro-SaaS factory blueprint."""

    if not settings.micro_saas_factory_enabled:
        return MicroSaasPublicBlueprintOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
        )

    return MicroSaasPublicBlueprintOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        phases=[dict(row) for row in MICRO_SAAS_BLUEPRINT],
        stack={
            "frontend": "Next.js 15 App Router",
            "backend": "FastAPI + LangGraph",
            "auth": "JWT dashboard sessions",
            "billing": "External billing provider (operator managed)",
            "deploy": "Docker Compose → K8s ready",
        },
        disclaimer="Blueprint only — simulate and verify each lane before live traffic.",
    )


async def compose_micro_saas_factory_snapshot(
    session: AsyncSession,
    *,
    tenant: Tenant | None,
) -> MicroSaasSnapshotOut:
    """Compose tenant Micro-SaaS factory readiness checklist."""

    if not settings.micro_saas_factory_enabled:
        return MicroSaasSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
        )

    profile = profile_from_tenant(tenant) if tenant is not None else None
    white_label = get_white_label_config(tenant) if tenant is not None else {}
    brand = str(white_label.get("brand_name") or "").strip()
    if profile is not None and profile.brand_name.strip():
        brand = profile.brand_name.strip()
    product_name = brand or "Micro-SaaS MVP"

    landing_done = bool(brand and brand not in {"Queenswarm", "Queenswarm Solo"})
    auth_done = True
    monetization_done = True

    github_active = False
    if tenant is not None:
        row = await DynamicConnectorService().fetch_by_slug(session, slug="github_rest")
        github_active = bool(row and row.is_active)
    deploy_done = github_active or bool((settings.domain or "").strip())

    steps = [
        MicroSaasStepOut(
            id="landing",
            label="Landing + brand",
            status="done" if landing_done else "pending",
            detail=f"Brand: {product_name}" if landing_done else "Set brand in Virtual Company or white-label.",
        ),
        MicroSaasStepOut(
            id="auth",
            label="Auth lane",
            status="done" if auth_done else "pending",
            detail="Dashboard JWT + tenant RBAC shipped in platform.",
        ),
        MicroSaasStepOut(
            id="monetization",
            label="Monetization lane",
            status="done" if monetization_done else "pending",
            detail="Handled outside Queenswarm runtime.",
        ),
        MicroSaasStepOut(
            id="deploy",
            label="Deploy recipe",
            status="done" if deploy_done else "pending",
            detail=(
                f"Domain {settings.domain} + GitHub connector ready."
                if deploy_done and github_active
                else f"Domain {settings.domain or 'unset'} — wire GitHub or deploy script."
            ),
        ),
    ]

    done_count = sum(1 for step in steps if step.status == "done")
    progress_pct = int(round(100 * done_count / max(len(steps), 1)))

    actions: list[MicroSaasActionOut] = []
    if not landing_done:
        actions.append(
            MicroSaasActionOut(
                id="brand",
                label="Define product brand",
                detail="Virtual Company profile or Settings → Enterprise white-label.",
                priority="high",
                href="/integrations?tab=virtual-company",
            ),
        )
    if not github_active:
        actions.append(
            MicroSaasActionOut(
                id="github",
                label="Install GitHub connector",
                detail="Enables Queen Maintainer deploy PR lane.",
                priority="medium",
                href="/integrations?tab=connectors",
            ),
        )
    if progress_pct >= 75:
        actions.append(
            MicroSaasActionOut(
                id="spawn_factory",
                label="Spawn Micro-SaaS Factory swarm",
                detail="Run factory routine: scope → landing → auth doc → deploy recipe.",
                priority="low",
                href="/swarms/new?template=micro-saas-factory",
            ),
        )

    return MicroSaasSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        progress_pct=progress_pct,
        product_name=product_name,
        deploy_domain=str(settings.domain or ""),
        steps=steps,
        blueprint=[dict(row) for row in MICRO_SAAS_BLUEPRINT],
        actions=actions[:6],
    )


__all__ = [
    "MicroSaasPublicBlueprintOut",
    "MicroSaasSnapshotOut",
    "build_public_micro_saas_blueprint",
    "compose_micro_saas_factory_snapshot",
]
