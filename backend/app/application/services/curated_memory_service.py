"""Tenant-scoped curated memory service used for Queen context bootstrap."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.memory.curated import CuratedFileKind, CuratedMemoryFile
from app.infrastructure.persistence.models.curated_memory import CuratedFileKindORM, CuratedMemoryORM

logger = get_logger(__name__)

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"s" r"k-" r"[a-zA-Z0-9]{20,}"),
    re.compile(r"BE" r"ARER\s+[A-Za-z0-9._-]{20,}", re.IGNORECASE),
    re.compile(r"API[_-]?" r"KEY[=:]\s*[A-Za-z0-9_-]{20,}", re.IGNORECASE),
)


class CuratedMemoryService:
    """CRUD and prompt rendering for curated Queen memory markdown files."""

    def __init__(self, *, db: AsyncSession) -> None:
        self._db = db

    async def get(self, tenant_id: uuid.UUID, kind: CuratedFileKind) -> CuratedMemoryFile | None:
        """Return one curated memory file for tenant/kind."""

        row = await self._get_row(tenant_id, kind)
        return self._to_domain(row) if row is not None else None

    async def upsert(
        self,
        tenant_id: uuid.UUID,
        kind: CuratedFileKind,
        content_md: str,
        user_id: uuid.UUID | None,
    ) -> CuratedMemoryFile:
        """Create or update one curated memory file after safety validation."""

        safe_content = content_md or ""
        char_count = len(safe_content)
        if char_count > 8000:
            msg = "Curated memory content exceeds 8000 characters."
            raise ValueError(msg)
        if self._looks_like_secret(safe_content):
            msg = "Curated memory content appears to include a secret-shaped token."
            raise ValueError(msg)

        row = await self._get_row(tenant_id, kind)
        if row is None:
            row = CuratedMemoryORM(
                tenant_id=tenant_id,
                kind=CuratedFileKindORM(kind.value),
                content_md=safe_content,
                version=1,
                updated_at=datetime.now(tz=UTC),
                updated_by_user_id=user_id,
                char_count=char_count,
            )
            self._db.add(row)
        else:
            row.content_md = safe_content
            row.version = int(row.version) + 1
            row.updated_by_user_id = user_id
            row.updated_at = datetime.now(tz=UTC)
            row.char_count = char_count
        await self._db.flush()
        return self._to_domain(row)

    async def get_bundle(self, tenant_id: uuid.UUID) -> dict[CuratedFileKind, str]:
        """Return all curated files, filling missing slots with empty strings."""

        rows = await self._list_rows_for_tenant(tenant_id)
        mapped: dict[CuratedFileKind, str] = {
            CuratedFileKind.MISSION: "",
            CuratedFileKind.IDEAL_STATE: "",
            CuratedFileKind.SOUL: "",
            CuratedFileKind.SKILLS_HIERARCHY: "",
            CuratedFileKind.INSTRUCTIONS: "",
        }
        for row in rows:
            kind = CuratedFileKind(str(row.kind))
            mapped[kind] = row.content_md or ""
        return mapped

    def render_brain_pack_export(self, bundle: dict[CuratedFileKind, str]) -> str:
        """Export Hermes-style brain pack as one markdown document."""

        soul = bundle.get(CuratedFileKind.SOUL, "")
        skills = bundle.get(CuratedFileKind.SKILLS_HIERARCHY, "")
        mission = bundle.get(CuratedFileKind.MISSION, "")
        ideal = bundle.get(CuratedFileKind.IDEAL_STATE, "")
        instructions = bundle.get(CuratedFileKind.INSTRUCTIONS, "")
        return (
            "# Operator Brain Pack\n\n"
            "## SOUL\n"
            f"{soul}\n\n"
            "## SKILLS HIERARCHY\n"
            f"{skills}\n\n"
            "## MEMORY — Mission\n"
            f"{mission}\n\n"
            "## MEMORY — Ideal state\n"
            f"{ideal}\n\n"
            "## USER — Behavioral instructions\n"
            f"{instructions}\n"
        )

    def render_prompt_prefix(self, bundle: dict[CuratedFileKind, str]) -> str:
        """Render stable context block prepended to Queen system prompts."""

        mission = bundle.get(CuratedFileKind.MISSION, "")
        ideal_state = bundle.get(CuratedFileKind.IDEAL_STATE, "")
        soul = bundle.get(CuratedFileKind.SOUL, "")
        skills_hierarchy = bundle.get(CuratedFileKind.SKILLS_HIERARCHY, "")
        instructions = bundle.get(CuratedFileKind.INSTRUCTIONS, "")
        return (
            "=== MISSION ===\n"
            f"{mission}\n"
            "=== IDEAL STATE ===\n"
            f"{ideal_state}\n"
            "=== SOUL ===\n"
            f"{soul}\n"
            "=== SKILLS HIERARCHY ===\n"
            f"{skills_hierarchy}\n"
            "=== BEHAVIORAL INSTRUCTIONS ===\n"
            f"{instructions}\n"
            "=== END CONTEXT ==="
        )

    async def clear(self, tenant_id: uuid.UUID, kind: CuratedFileKind) -> None:
        """Delete one curated file for tenant/kind."""

        await self._db.execute(
            delete(CuratedMemoryORM).where(
                CuratedMemoryORM.tenant_id == tenant_id,
                CuratedMemoryORM.kind == CuratedFileKindORM(kind.value),
            ),
        )
        await self._db.flush()

    async def seed_starter_pack(
        self,
        tenant_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None,
        overwrite: bool = False,
    ) -> tuple[list[str], list[str]]:
        """Fill empty curated slots with Queenswarm solo-operator starter markdown."""

        from app.application.services.brain_pack_starters import BRAIN_PACK_STARTERS

        bundle = await self.get_bundle(tenant_id)
        seeded: list[str] = []
        skipped: list[str] = []
        for kind, content in BRAIN_PACK_STARTERS.items():
            existing = (bundle.get(kind) or "").strip()
            if existing and not overwrite:
                skipped.append(kind.value)
                continue
            await self.upsert(tenant_id=tenant_id, kind=kind, content_md=content, user_id=user_id)
            seeded.append(kind.value)
        return seeded, skipped

    async def _get_row(self, tenant_id: uuid.UUID, kind: CuratedFileKind) -> CuratedMemoryORM | None:
        return await self._db.scalar(
            select(CuratedMemoryORM).where(
                CuratedMemoryORM.tenant_id == tenant_id,
                CuratedMemoryORM.kind == CuratedFileKindORM(kind.value),
            ),
        )

    async def _list_rows_for_tenant(self, tenant_id: uuid.UUID) -> list[CuratedMemoryORM]:
        result = await self._db.scalars(
            select(CuratedMemoryORM).where(CuratedMemoryORM.tenant_id == tenant_id),
        )
        return list(result)

    def _looks_like_secret(self, content_md: str) -> bool:
        return any(pattern.search(content_md) is not None for pattern in _SECRET_PATTERNS)

    def _to_domain(self, row: CuratedMemoryORM) -> CuratedMemoryFile:
        return CuratedMemoryFile(
            tenant_id=row.tenant_id,
            kind=CuratedFileKind(row.kind.value),
            content_md=row.content_md,
            version=int(row.version),
            updated_at=row.updated_at,
            updated_by_user_id=row.updated_by_user_id,
            char_count=int(row.char_count),
        )


__all__ = ["CuratedMemoryService"]
