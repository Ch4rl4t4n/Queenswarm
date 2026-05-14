"""Pytest bootstrap ensuring Pydantic settings resolve without a developer ``.env``."""

from __future__ import annotations

import os

# Prime before any test module imports ``app.core.config`` (executes on conftest load).
_TEST_ENV: dict[str, str] = {
    "GROK_API_KEY": "xai-unit-test-placeholder",
    "ANTHROPIC_API_KEY": "sk-ant-unit-test-placeholder",
    "POSTGRES_URL": "postgresql+asyncpg://queenswarm:unit_test@localhost:5432/queenswarm_unit",
    "POSTGRES_USER": "queenswarm",
    "POSTGRES_PASSWORD": "unit_test",
    "REDIS_URL": "redis://localhost:6379/15",
    "NEO4J_URI": "bolt://localhost:7688",
    "NEO4J_USER": "neo4j",
    "NEO4J_PASSWORD": "unit_test_secret",
    "SECRET_KEY": "unit-test-secret-key-at-least-thirty-two-chars",
    "HIVE_WAGGLE_RELAY_ENABLED": "false",
    "RATE_LIMIT_ENABLED": "false",
    "RECIPE_CATALOG_MUTATIONS_ENABLED": "true",
    "BALLROOM_CAPSULE_BACKEND": "memory",
    "BALLROOM_CAPSULE_TTL_SEC": "86400",
}
for _key, _value in _TEST_ENV.items():
    os.environ.setdefault(_key, _value)


def pytest_configure(config) -> None:  # noqa: ANN001
    """Reset cached settings singleton so optional env overrides during collection apply."""

    from app.core.config import get_settings
    from app.models import load_all_models

    load_all_models()
    get_settings.cache_clear()

