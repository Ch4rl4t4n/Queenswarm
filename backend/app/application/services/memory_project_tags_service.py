"""MEM5 — Client/project memory tags + recall filter (team slice / RLS-style)."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.knowledge import KnowledgeItem
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

MEMORY_PROJECT_TAGS_BUCKET = "memory_project_tags"
MEM5_TOPIC_PREFIX = "mem5:"
MemoryProjectTagKind = Literal["client", "project"]
_MAX_TAGS = 48
_TAG_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,62}$")


class MemoryProjectTagOut(BaseModel):
    """One client or project memory slice tag."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    kind: MemoryProjectTagKind
    description: str = ""
    color_hex: str | None = None
    created_at: str
    knowledge_count: int = 0


class MemoryProjectTagsSnapshotOut(BaseModel):
    """Tenant tag registry + active recall filter."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    tags: list[MemoryProjectTagOut] = Field(default_factory=list)
    active_filter_tag_ids: list[str] = Field(default_factory=list)
    active_filter_labels: list[str] = Field(default_factory=list)
    filter_active: bool = False
    operator_hint: str = "Tag clients and projects — recall filters to matching hive memory only."


class MemoryProjectTagUpsertIn(BaseModel):
    """Create or update one memory project tag."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    label: str = Field(min_length=2, max_length=80)
    kind: MemoryProjectTagKind = "project"
    description: str = Field(default="", max_length=400)
    color_hex: str | None = Field(default=None, max_length=16)

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        token = value.strip().lower()
        if not _TAG_ID_RE.fullmatch(token):
            raise ValueError("Tag id must be 2–63 lowercase alphanumeric, dash, or underscore.")
        return token


class MemoryProjectTagAssignIn(BaseModel):
    """Assign memory project tags to a knowledge item."""

    model_config = ConfigDict(extra="forbid")

    knowledge_item_id: uuid.UUID
    tag_ids: list[str] = Field(default_factory=list, max_length=8)


class ActiveRecallFilterPatch(BaseModel):
    """Set active RLS-style recall slice."""

    model_config = ConfigDict(extra="forbid")

    tag_ids: list[str] = Field(default_factory=list, max_length=8)


def _tags_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get(MEMORY_PROJECT_TAGS_BUCKET)
    return dict(bucket) if isinstance(bucket, dict) else {}


def topic_tag_for_memory_project(tag_id: str) -> str:
    """Canonical topic tag token for knowledge rows and vector metadata."""

    return f"{MEM5_TOPIC_PREFIX}{tag_id.strip().lower()}"


def parse_memory_project_tag_ids_from_topic_tags(topic_tags: list[str] | None) -> list[str]:
    """Extract mem5 tag ids from knowledge topic_tags."""

    ids: list[str] = []
    for raw in topic_tags or []:
        token = str(raw or "").strip().lower()
        if token.startswith(MEM5_TOPIC_PREFIX):
            tag_id = token[len(MEM5_TOPIC_PREFIX) :]
            if tag_id and tag_id not in ids:
                ids.append(tag_id)
    return ids


def parse_memory_project_tag_ids_from_metadata(metadata: dict[str, Any] | None) -> list[str]:
    """Read tag ids from vector metadata or session context."""

    meta = dict(metadata or {})
    direct = meta.get("memory_project_tag_ids")
    if isinstance(direct, list):
        return [str(item).strip().lower() for item in direct if str(item).strip()]
    tags = meta.get("tags")
    if isinstance(tags, str):
        tags = [part.strip() for part in tags.split(",") if part.strip()]
    if isinstance(tags, list):
        return parse_memory_project_tag_ids_from_topic_tags([str(item) for item in tags])
    return []


def merge_memory_project_tags_root(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    """Return operator_settings with initialized memory_project_tags bucket."""

    root = dict(operator_settings or {})
    bucket = _tags_bucket(root)
    bucket.setdefault("tags", [])
    bucket.setdefault("active_filter_tag_ids", [])
    root[MEMORY_PROJECT_TAGS_BUCKET] = bucket
    return root


def _normalize_tag_row(raw: dict[str, Any]) -> dict[str, Any] | None:
    tag_id = str(raw.get("id") or "").strip().lower()
    label = str(raw.get("label") or "").strip()
    if not tag_id or not label:
        return None
    kind = str(raw.get("kind") or "project").strip().lower()
    if kind not in {"client", "project"}:
        kind = "project"
    return {
        "id": tag_id,
        "label": label[:80],
        "kind": kind,
        "description": str(raw.get("description") or "")[:400],
        "color_hex": str(raw.get("color_hex") or "").strip() or None,
        "created_at": str(raw.get("created_at") or datetime.now(tz=UTC).isoformat()),
    }


def _slugify_tag_id(label: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", label.strip().lower()).strip("-")
    token = token[:48] or "tag"
    if not _TAG_ID_RE.fullmatch(token):
        token = f"tag-{token[:40]}".strip("-")
    return token


def tags_from_tenant(tenant: Tenant | None) -> list[dict[str, Any]]:
    """Load normalized tag rows from tenant operator_settings."""

    bucket = _tags_bucket(tenant.operator_settings if tenant is not None else None)
    rows: list[dict[str, Any]] = []
    for raw in bucket.get("tags") or []:
        if not isinstance(raw, dict):
            continue
        normalized = _normalize_tag_row(raw)
        if normalized is not None:
            rows.append(normalized)
    return rows[:_MAX_TAGS]


def active_filter_tag_ids_from_tenant(tenant: Tenant | None) -> list[str]:
    """Return active recall filter tag ids."""

    bucket = _tags_bucket(tenant.operator_settings if tenant is not None else None)
    known = {row["id"] for row in tags_from_tenant(tenant)}
    active: list[str] = []
    for raw in bucket.get("active_filter_tag_ids") or []:
        tag_id = str(raw or "").strip().lower()
        if tag_id and tag_id in known and tag_id not in active:
            active.append(tag_id)
    return active


def resolve_recall_filter_tag_ids(
    tenant: Tenant | None,
    *,
    requested_tag_ids: list[str] | None = None,
) -> list[str]:
    """Merge explicit query filter with tenant active slice."""

    known = {row["id"] for row in tags_from_tenant(tenant)}
    if requested_tag_ids:
        resolved = [
            str(tag_id).strip().lower()
            for tag_id in requested_tag_ids
            if str(tag_id).strip().lower() in known
        ]
        return list(dict.fromkeys(resolved))
    return active_filter_tag_ids_from_tenant(tenant)


def source_matches_memory_project_filter(
    *,
    source_tag_ids: list[str],
    filter_tag_ids: list[str],
) -> bool:
    """RLS-style inclusion — untagged sources excluded when filter active."""

    if not filter_tag_ids:
        return True
    if not source_tag_ids:
        return False
    wanted = set(filter_tag_ids)
    return bool(wanted.intersection(source_tag_ids))


async def _count_knowledge_by_tag(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    tag_ids: list[str],
) -> dict[str, int]:
    if not tag_ids:
        return {}
    stmt = select(KnowledgeItem).where(KnowledgeItem.tenant_id == tenant_id)
    rows = list((await session.scalars(stmt)).all())
    counts = dict.fromkeys(tag_ids, 0)
    for row in rows:
        row_tags = parse_memory_project_tag_ids_from_topic_tags(list(row.topic_tags or []))
        for tag_id in row_tags:
            if tag_id in counts:
                counts[tag_id] += 1
    return counts


async def compose_memory_project_tags_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    tenant: Tenant | None,
) -> MemoryProjectTagsSnapshotOut:
    """Return tag registry, counts, and active recall filter."""

    if not settings.memory_project_tags_enabled:
        return MemoryProjectTagsSnapshotOut(
            enabled=False,
            operator_hint="Client/project memory tags disabled.",
        )

    raw_tags = tags_from_tenant(tenant)
    tag_ids = [row["id"] for row in raw_tags]
    counts = await _count_knowledge_by_tag(session, tenant_id=tenant_id, tag_ids=tag_ids)
    active_ids = active_filter_tag_ids_from_tenant(tenant)
    label_by_id = {row["id"]: row["label"] for row in raw_tags}

    tags = [
        MemoryProjectTagOut(
            id=row["id"],
            label=row["label"],
            kind=row["kind"],  # type: ignore[arg-type]
            description=row.get("description") or "",
            color_hex=row.get("color_hex"),
            created_at=row["created_at"],
            knowledge_count=int(counts.get(row["id"], 0)),
        )
        for row in raw_tags
    ]

    if not tags:
        hint = "Create client or project tags — assign them on knowledge captures to slice recall."
    elif active_ids:
        labels = ", ".join(label_by_id.get(tag_id, tag_id) for tag_id in active_ids[:3])
        hint = f"Recall filter active — only memory tagged for {labels} is included."
    else:
        hint = "No recall filter — all hive memory sources eligible. Select tags to slice like GBrain company brain."

    return MemoryProjectTagsSnapshotOut(
        enabled=True,
        tags=tags,
        active_filter_tag_ids=active_ids,
        active_filter_labels=[label_by_id.get(tag_id, tag_id) for tag_id in active_ids],
        filter_active=bool(active_ids),
        operator_hint=hint,
    )


def upsert_memory_project_tag(
    tenant: Tenant,
    payload: MemoryProjectTagUpsertIn,
) -> MemoryProjectTagOut:
    """Create or update one tag in tenant operator_settings."""

    if not settings.memory_project_tags_enabled:
        raise ValueError("Client/project memory tags are disabled.")

    root = merge_memory_project_tags_root(tenant.operator_settings)
    bucket = dict(root[MEMORY_PROJECT_TAGS_BUCKET])
    rows = [dict(item) for item in bucket.get("tags") or [] if isinstance(item, dict)]
    tag_id = payload.id or _slugify_tag_id(payload.label)
    if not _TAG_ID_RE.fullmatch(tag_id):
        raise ValueError("Could not derive a valid tag id.")

    now = datetime.now(tz=UTC).isoformat()
    updated_row = {
        "id": tag_id,
        "label": payload.label.strip(),
        "kind": payload.kind,
        "description": payload.description.strip(),
        "color_hex": payload.color_hex,
        "created_at": now,
    }

    replaced = False
    for index, row in enumerate(rows):
        if str(row.get("id") or "").strip().lower() == tag_id:
            updated_row["created_at"] = str(row.get("created_at") or now)
            rows[index] = updated_row
            replaced = True
            break
    if not replaced:
        if len(rows) >= _MAX_TAGS:
            raise ValueError(f"Maximum {_MAX_TAGS} client/project tags reached.")
        rows.append(updated_row)

    bucket["tags"] = rows[:_MAX_TAGS]
    root[MEMORY_PROJECT_TAGS_BUCKET] = bucket
    tenant.operator_settings = root

    _logger.info(
        "memory_project_tags.upsert",
        agent_id="memory_project_tags",
        swarm_id=str(tenant.id),
        tag_id=tag_id,
        kind=payload.kind,
    )
    return MemoryProjectTagOut(
        id=tag_id,
        label=updated_row["label"],
        kind=payload.kind,
        description=updated_row["description"],
        color_hex=updated_row.get("color_hex"),
        created_at=updated_row["created_at"],
        knowledge_count=0,
    )


def delete_memory_project_tag(tenant: Tenant, tag_id: str) -> bool:
    """Remove tag and drop from active filter."""

    token = tag_id.strip().lower()
    root = merge_memory_project_tags_root(tenant.operator_settings)
    bucket = dict(root[MEMORY_PROJECT_TAGS_BUCKET])
    rows = [dict(item) for item in bucket.get("tags") or [] if isinstance(item, dict)]
    kept = [row for row in rows if str(row.get("id") or "").strip().lower() != token]
    if len(kept) == len(rows):
        return False
    bucket["tags"] = kept
    bucket["active_filter_tag_ids"] = [
        str(item).strip().lower()
        for item in list(bucket.get("active_filter_tag_ids") or [])
        if str(item).strip().lower() != token
    ]
    root[MEMORY_PROJECT_TAGS_BUCKET] = bucket
    tenant.operator_settings = root
    _logger.info(
        "memory_project_tags.delete",
        agent_id="memory_project_tags",
        swarm_id=str(tenant.id),
        tag_id=token,
    )
    return True


def set_active_recall_filter(tenant: Tenant, patch: ActiveRecallFilterPatch) -> list[str]:
    """Persist active recall slice tag ids."""

    if not settings.memory_project_tags_enabled:
        raise ValueError("Client/project memory tags are disabled.")

    known = {row["id"] for row in tags_from_tenant(tenant)}
    active = [
        str(tag_id).strip().lower()
        for tag_id in patch.tag_ids
        if str(tag_id).strip().lower() in known
    ]
    active = list(dict.fromkeys(active))[:8]

    root = merge_memory_project_tags_root(tenant.operator_settings)
    bucket = dict(root[MEMORY_PROJECT_TAGS_BUCKET])
    bucket["active_filter_tag_ids"] = active
    root[MEMORY_PROJECT_TAGS_BUCKET] = bucket
    tenant.operator_settings = root
    _logger.info(
        "memory_project_tags.filter",
        agent_id="memory_project_tags",
        swarm_id=str(tenant.id),
        active_count=len(active),
    )
    return active


async def assign_memory_project_tags_to_knowledge(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    payload: MemoryProjectTagAssignIn,
    tenant: Tenant,
) -> list[str]:
    """Assign mem5 topic tags on a knowledge item."""

    known = {row["id"] for row in tags_from_tenant(tenant)}
    wanted = [tag_id for tag_id in payload.tag_ids if tag_id.strip().lower() in known]
    wanted = list(dict.fromkeys([tag_id.strip().lower() for tag_id in wanted]))[:8]

    row = await session.get(KnowledgeItem, payload.knowledge_item_id)
    if row is None or row.tenant_id != tenant_id:
        raise ValueError("Knowledge item not found for tenant.")

    preserved = [
        tag
        for tag in list(row.topic_tags or [])
        if not str(tag).startswith(MEM5_TOPIC_PREFIX)
    ]
    mem5_tags = [topic_tag_for_memory_project(tag_id) for tag_id in wanted]
    row.topic_tags = list(dict.fromkeys([*preserved, *mem5_tags]))[:32]
    await session.flush()
    return wanted


def curated_kind_tag_ids(tenant: Tenant | None, kind: str) -> list[str]:
    """Return assigned memory project tag ids for one curated Brain Pack kind."""

    if tenant is None:
        return []
    bucket = _tags_bucket(tenant.operator_settings)
    assignments = dict(bucket.get("curated_assignments") or {})
    raw = assignments.get(kind)
    if not isinstance(raw, list):
        return []
    known = {row["id"] for row in tags_from_tenant(tenant)}
    return [str(item).strip().lower() for item in raw if str(item).strip().lower() in known]


async def assign_curated_kind_tags(
    tenant: Tenant,
    *,
    kind: str,
    tag_ids: list[str],
) -> list[str]:
    """Assign memory project tags to one Brain Pack curated kind."""

    known = {row["id"] for row in tags_from_tenant(tenant)}
    wanted = list(dict.fromkeys([tag_id.strip().lower() for tag_id in tag_ids if tag_id.strip().lower() in known]))[:8]
    root = merge_memory_project_tags_root(tenant.operator_settings)
    bucket = dict(root[MEMORY_PROJECT_TAGS_BUCKET])
    assignments = dict(bucket.get("curated_assignments") or {})
    assignments[kind] = wanted
    bucket["curated_assignments"] = assignments
    root[MEMORY_PROJECT_TAGS_BUCKET] = bucket
    tenant.operator_settings = root
    return wanted


__all__ = [
    "MEM5_TOPIC_PREFIX",
    "MEMORY_PROJECT_TAGS_BUCKET",
    "ActiveRecallFilterPatch",
    "MemoryProjectTagAssignIn",
    "MemoryProjectTagOut",
    "MemoryProjectTagsSnapshotOut",
    "MemoryProjectTagUpsertIn",
    "active_filter_tag_ids_from_tenant",
    "assign_memory_project_tags_to_knowledge",
    "assign_curated_kind_tags",
    "compose_memory_project_tags_snapshot",
    "curated_kind_tag_ids",
    "delete_memory_project_tag",
    "merge_memory_project_tags_root",
    "parse_memory_project_tag_ids_from_metadata",
    "parse_memory_project_tag_ids_from_topic_tags",
    "resolve_recall_filter_tag_ids",
    "set_active_recall_filter",
    "source_matches_memory_project_filter",
    "topic_tag_for_memory_project",
    "tags_from_tenant",
    "upsert_memory_project_tag",
]
