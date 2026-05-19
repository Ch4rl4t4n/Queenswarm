"""Tenant-scoped CRUD service for dynamic agent templates."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.agent_template import AgentTemplateORM


class AgentTemplateService:
    """CRUD operations for `AgentTemplateORM` constrained by tenant."""

    def __init__(self, *, db: AsyncSession) -> None:
        """Initialize service with request-scoped async DB session."""

        self._db = db

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[AgentTemplateORM]:
        """List all templates for one tenant sorted by defaults first."""

        rows = await self._db.scalars(
            select(AgentTemplateORM)
            .where(AgentTemplateORM.tenant_id == tenant_id)
            .order_by(AgentTemplateORM.is_default.desc(), AgentTemplateORM.name.asc()),
        )
        return list(rows)

    async def get_by_id(self, tenant_id: uuid.UUID, template_id: uuid.UUID) -> AgentTemplateORM | None:
        """Fetch one template by id within tenant boundary."""

        return await self._db.scalar(
            select(AgentTemplateORM).where(
                AgentTemplateORM.id == template_id,
                AgentTemplateORM.tenant_id == tenant_id,
            ),
        )

    async def create(
        self,
        *,
        tenant_id: uuid.UUID,
        name: str,
        description: str,
        icon: str,
        category: str,
        tools: list[str],
        prompt_template: str,
        is_default: bool,
    ) -> AgentTemplateORM:
        """Create tenant-owned template."""

        if is_default:
            await self._clear_default_flag(tenant_id)
        row = AgentTemplateORM(
            tenant_id=tenant_id,
            name=name.strip(),
            description=description.strip(),
            icon=icon.strip(),
            category=category.strip() or "general",
            tools=[item.strip() for item in tools if item.strip()],
            prompt_template=prompt_template.strip(),
            is_default=bool(is_default),
        )
        self._db.add(row)
        await self._db.flush()
        return row

    async def update(
        self,
        *,
        tenant_id: uuid.UUID,
        template_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
        icon: str | None = None,
        category: str | None = None,
        tools: list[str] | None = None,
        prompt_template: str | None = None,
        is_default: bool | None = None,
    ) -> AgentTemplateORM | None:
        """Update tenant template and return updated row, or None when missing."""

        row = await self.get_by_id(tenant_id, template_id)
        if row is None:
            return None
        if name is not None:
            row.name = name.strip()
        if description is not None:
            row.description = description.strip()
        if icon is not None:
            row.icon = icon.strip()
        if category is not None:
            row.category = category.strip() or "general"
        if tools is not None:
            row.tools = [item.strip() for item in tools if item.strip()]
        if prompt_template is not None:
            row.prompt_template = prompt_template.strip()
        if is_default is not None:
            if is_default:
                await self._clear_default_flag(tenant_id, exclude_template_id=row.id)
            row.is_default = bool(is_default)
        await self._db.flush()
        return row

    async def delete(self, tenant_id: uuid.UUID, template_id: uuid.UUID) -> bool:
        """Delete one tenant template. Returns True when row existed."""

        result = await self._db.execute(
            delete(AgentTemplateORM).where(
                AgentTemplateORM.id == template_id,
                AgentTemplateORM.tenant_id == tenant_id,
            ),
        )
        await self._db.flush()
        return bool(result.rowcount and result.rowcount > 0)

    async def _clear_default_flag(self, tenant_id: uuid.UUID, *, exclude_template_id: uuid.UUID | None = None) -> None:
        """Ensure only one default template per tenant."""

        rows = await self._db.scalars(
            select(AgentTemplateORM).where(
                AgentTemplateORM.tenant_id == tenant_id,
            ),
        )
        for row in rows:
            if exclude_template_id is not None and row.id == exclude_template_id:
                continue
            if row.is_default:
                row.is_default = False


__all__ = ["AgentTemplateService"]
