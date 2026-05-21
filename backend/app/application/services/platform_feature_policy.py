"""Load and persist admin platform feature policy overrides."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.platform_feature_policy import PlatformFeaturePolicy


async def load_policy_overrides(db: AsyncSession) -> dict[tuple[str, str], bool]:
    """Return all persisted feature/profile switches."""

    rows = list((await db.scalars(select(PlatformFeaturePolicy))).all())
    return {(str(row.feature_key), str(row.profile_key)): bool(row.enabled) for row in rows}


async def upsert_policy_overrides(
    db: AsyncSession,
    *,
    updates: list[dict[str, object]],
) -> dict[tuple[str, str], bool]:
    """Apply bulk matrix cell updates and return the merged override map."""

    merged = await load_policy_overrides(db)
    for raw in updates:
        feature_key = str(raw.get("feature_key", "")).strip()
        profile_key = str(raw.get("profile_key", "")).strip()
        if not feature_key or not profile_key:
            continue
        enabled = bool(raw.get("enabled"))
        stmt = (
            insert(PlatformFeaturePolicy)
            .values(feature_key=feature_key, profile_key=profile_key, enabled=enabled)
            .on_conflict_do_update(
                index_elements=["feature_key", "profile_key"],
                set_={"enabled": enabled},
            )
        )
        await db.execute(stmt)
        merged[(feature_key, profile_key)] = enabled
    await db.flush()
    return merged


async def delete_policy_override(
    db: AsyncSession,
    *,
    feature_key: str,
    profile_key: str,
) -> None:
    """Remove one override so catalog defaults apply again."""

    row = await db.scalar(
        select(PlatformFeaturePolicy).where(
            PlatformFeaturePolicy.feature_key == feature_key.strip(),
            PlatformFeaturePolicy.profile_key == profile_key.strip(),
        ),
    )
    if row is not None:
        await db.delete(row)
        await db.flush()


__all__ = ["delete_policy_override", "load_policy_overrides", "upsert_policy_overrides"]
