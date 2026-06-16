"""Track M LOC8 — Tenant local adapter registry (LoRA/GGUF → LiteLLM slug)."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.unsloth_bridge_service import (
    litellm_slug_from_ollama_tag,
    normalize_ollama_model_name,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.tenant_local_adapter import TenantLocalAdapterORM

_logger = get_logger(__name__)

LocalAdapterKind = Literal["gguf", "lora"]


class LocalAdapterOut(BaseModel):
    """One tenant adapter row."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    ollama_tag: str
    litellm_slug: str
    kind: LocalAdapterKind
    base_model: str | None = None
    source_path: str | None = None
    is_active: bool = False


class LocalAdapterRegistrySnapshotOut(BaseModel):
    """Settings snapshot for adapter registry panel."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    adapters: list[LocalAdapterOut] = Field(default_factory=list)
    active_slug: str | None = None
    operator_hint: str = ""


class LocalAdapterRegisterIn(BaseModel):
    """Register adapter after Unsloth/Ollama import."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    ollama_tag: str = Field(min_length=2, max_length=64)
    kind: LocalAdapterKind = "gguf"
    base_model: str | None = Field(default=None, max_length=128)
    source_path: str | None = Field(default=None, max_length=512)
    activate: bool = False

    @field_validator("ollama_tag")
    @classmethod
    def _normalize_tag(cls, value: str) -> str:
        return normalize_ollama_model_name(value)


def _serialize(row: TenantLocalAdapterORM) -> LocalAdapterOut:
    return LocalAdapterOut(
        id=str(row.id),
        name=row.name,
        ollama_tag=row.ollama_tag,
        litellm_slug=row.litellm_slug,
        kind=row.kind if row.kind in {"gguf", "lora"} else "gguf",
        base_model=row.base_model,
        source_path=row.source_path,
        is_active=bool(row.is_active),
    )


async def list_tenant_local_adapter_slugs(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> list[str]:
    """Return LiteLLM slugs for tenant adapters (active first)."""

    if not settings.local_adapter_registry_enabled:
        return []
    rows = list(
        (
            await session.scalars(
                select(TenantLocalAdapterORM)
                .where(TenantLocalAdapterORM.tenant_id == tenant_id)
                .order_by(TenantLocalAdapterORM.is_active.desc(), TenantLocalAdapterORM.updated_at.desc()),
            )
        ).all(),
    )
    return [row.litellm_slug for row in rows if row.litellm_slug.strip()]


async def compose_local_adapter_registry_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> LocalAdapterRegistrySnapshotOut:
    """Build operator snapshot for Settings UI."""

    enabled = settings.local_llm_enabled and settings.local_adapter_registry_enabled
    if not enabled:
        return LocalAdapterRegistrySnapshotOut(
            enabled=False,
            operator_hint="Enable LOCAL_LLM_ENABLED and local_adapter_registry to manage adapters.",
        )

    rows = list(
        (
            await session.scalars(
                select(TenantLocalAdapterORM)
                .where(TenantLocalAdapterORM.tenant_id == tenant_id)
                .order_by(TenantLocalAdapterORM.is_active.desc(), TenantLocalAdapterORM.updated_at.desc()),
            )
        ).all(),
    )
    adapters = [_serialize(row) for row in rows]
    active = next((a.litellm_slug for a in adapters if a.is_active), None)
    return LocalAdapterRegistrySnapshotOut(
        enabled=True,
        adapters=adapters,
        active_slug=active,
        operator_hint="Import via ./scripts/operator-unsloth-bridge.sh then register the Ollama tag here.",
    )


async def register_local_adapter(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    payload: LocalAdapterRegisterIn,
) -> LocalAdapterOut:
    """Upsert tenant adapter metadata after Ollama import."""

    tag = normalize_ollama_model_name(payload.ollama_tag)
    slug = litellm_slug_from_ollama_tag(tag)
    existing = await session.scalar(
        select(TenantLocalAdapterORM).where(
            TenantLocalAdapterORM.tenant_id == tenant_id,
            TenantLocalAdapterORM.ollama_tag == tag,
        ),
    )
    if existing is None:
        row = TenantLocalAdapterORM(
            tenant_id=tenant_id,
            name=payload.name.strip(),
            ollama_tag=tag,
            litellm_slug=slug,
            kind=payload.kind,
            base_model=payload.base_model,
            source_path=payload.source_path,
            is_active=False,
            metadata_json={},
        )
        session.add(row)
    else:
        row = existing
        row.name = payload.name.strip()
        row.litellm_slug = slug
        row.kind = payload.kind
        row.base_model = payload.base_model
        row.source_path = payload.source_path

    if payload.activate:
        await session.execute(
            update(TenantLocalAdapterORM)
            .where(
                TenantLocalAdapterORM.tenant_id == tenant_id,
                TenantLocalAdapterORM.id != row.id,
            )
            .values(is_active=False),
        )
        row.is_active = True

    await session.commit()
    await session.refresh(row)
    _logger.info(
        "local_adapter_registry.registered",
        tenant_id=str(tenant_id),
        ollama_tag=tag,
        litellm_slug=slug,
        is_active=row.is_active,
    )
    return _serialize(row)


async def activate_local_adapter(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    adapter_id: uuid.UUID,
) -> LocalAdapterOut:
    """Mark one adapter active for local_sovereign routing hints."""

    row = await session.get(TenantLocalAdapterORM, adapter_id)
    if row is None or row.tenant_id != tenant_id:
        msg = "Adapter not found."
        raise LookupError(msg)

    await session.execute(
        update(TenantLocalAdapterORM)
        .where(TenantLocalAdapterORM.tenant_id == tenant_id)
        .values(is_active=False),
    )
    row.is_active = True
    await session.commit()
    await session.refresh(row)
    return _serialize(row)


async def delete_local_adapter(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    adapter_id: uuid.UUID,
) -> None:
    """Remove adapter registry row (does not delete Ollama weights)."""

    row = await session.get(TenantLocalAdapterORM, adapter_id)
    if row is None or row.tenant_id != tenant_id:
        msg = "Adapter not found."
        raise LookupError(msg)
    await session.delete(row)
    await session.commit()


__all__ = [
    "LocalAdapterOut",
    "LocalAdapterRegisterIn",
    "LocalAdapterRegistrySnapshotOut",
    "activate_local_adapter",
    "compose_local_adapter_registry_snapshot",
    "delete_local_adapter",
    "list_tenant_local_adapter_slugs",
    "register_local_adapter",
]
