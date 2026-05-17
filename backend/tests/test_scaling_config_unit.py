"""Unit tests for scaling-mode configuration constraints."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _base_kwargs() -> dict[str, object]:
    return {
        "postgres_url": "postgresql+asyncpg://queenswarm:devpass@localhost:5432/queenswarm",
        "postgres_user": "queenswarm",
        "postgres_password": "devpass",
        "postgres_db": "queenswarm",
        "redis_url": "redis://localhost:6379/0",
        "neo4j_uri": "bolt://localhost:7687",
        "neo4j_user": "neo4j",
        "neo4j_password": "changeme_strong_password",
        "secret_key": "x" * 64,
    }


def test_settings_when_scaling_enabled_and_memory_ballroom_then_validation_error() -> None:
    payload = _base_kwargs()
    payload["scaling_mode_enabled"] = True
    payload["ballroom_capsule_backend"] = "memory"
    with pytest.raises(ValidationError):
        Settings(**payload)


def test_settings_when_instance_id_blank_then_auto_populated() -> None:
    payload = _base_kwargs()
    payload["instance_id"] = "   "
    settings = Settings(**payload)
    assert settings.instance_id.startswith("api-")


def test_settings_when_ha_lists_from_csv_then_normalized() -> None:
    payload = _base_kwargs()
    payload["redis_failover_urls"] = " redis://redis-a:6379/0 , redis://redis-b:6379/0 "
    payload["postgres_replica_urls"] = "postgresql+asyncpg://replica-a/db,postgresql+asyncpg://replica-b/db"
    settings = Settings(**payload)
    assert settings.redis_failover_urls == ["redis://redis-a:6379/0", "redis://redis-b:6379/0"]
    assert settings.postgres_replica_urls == [
        "postgresql+asyncpg://replica-a/db",
        "postgresql+asyncpg://replica-b/db",
    ]
