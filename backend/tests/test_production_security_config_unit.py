"""Unit tests for production security mode configuration constraints."""

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
        "connector_vault_fernet_key": "Q4BX4-zvQ8z8eA3WQq6xaA2ovA1w_a3fHjJO8nV6a8U=",
    }


def test_settings_when_production_mode_and_secret_too_short_then_validation_error() -> None:
    payload = _base_kwargs()
    payload["production_security_mode"] = True
    payload["secret_key"] = "short-secret"
    with pytest.raises(ValidationError):
        Settings(**payload)


def test_settings_when_production_mode_and_missing_connector_vault_key_then_validation_error() -> None:
    payload = _base_kwargs()
    payload["production_security_mode"] = True
    payload["connector_vault_fernet_key"] = ""
    with pytest.raises(ValidationError):
        Settings(**payload)


def test_settings_when_production_mode_and_valid_constraints_then_builds() -> None:
    payload = _base_kwargs()
    payload["production_security_mode"] = True
    payload["access_token_expire_minutes"] = 15
    payload["refresh_token_expire_days"] = 7
    settings = Settings(**payload)
    assert settings.production_security_mode is True
    assert settings.access_token_expire_minutes == 15
