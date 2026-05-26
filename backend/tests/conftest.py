"""Pytest bootstrap ensuring Pydantic settings resolve without a developer ``.env``."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock

import pytest

# Prime before any test module imports ``app.core.config`` (executes on conftest load).
# Force overrides — prod/docker env must not leak into unit tests (solo mode, security mode, short keys).
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
    "SECRET_KEY": "unit-test-secret-key-at-least-sixty-four-characters-long-for-pydantic-validation",
    "PRODUCTION_SECURITY_MODE": "false",
    "SOLO_MODE_ENABLED": "false",
    "HIVE_WAGGLE_RELAY_ENABLED": "false",
    "RATE_LIMIT_ENABLED": "false",
    "RECIPE_CATALOG_MUTATIONS_ENABLED": "true",
    "BALLROOM_CAPSULE_BACKEND": "memory",
    "BALLROOM_CAPSULE_TTL_SEC": "86400",
}
for _key, _value in _TEST_ENV.items():
    os.environ[_key] = _value


@pytest.fixture(autouse=True)
def _stub_redis_for_unit_tests(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent unit tests from opening real Redis connections (except redis-focused suites)."""

    node_path = str(getattr(request.node, "fspath", ""))
    if "/test_redis_" in node_path or "/test_distributed_locking_" in node_path:
        return

    fake = AsyncMock()
    fake.eval = AsyncMock(return_value=1)
    fake.get = AsyncMock(return_value=None)
    fake.set = AsyncMock(return_value=True)
    fake.setex = AsyncMock(return_value=True)
    fake.ping = AsyncMock(return_value=True)
    fake.delete = AsyncMock(return_value=1)
    fake.zadd = AsyncMock(return_value=1)
    fake.zcard = AsyncMock(return_value=0)
    fake.zremrangebyscore = AsyncMock(return_value=0)
    fake.expire = AsyncMock(return_value=True)

    async def _with_fake(client_op):  # noqa: ANN001
        return await client_op(fake)

    monkeypatch.setattr("app.core.redis_client._with_redis_client", _with_fake)

    async def _reserve_ok(*_args: object, **_kwargs: object) -> bool:
        return True

    monkeypatch.setattr("app.core.redis_client.sliding_window_reserve", _reserve_ok)

    async def _set_json_noop(*_args: object, **_kwargs: object) -> None:
        return None

    async def _get_json_noop(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr("app.core.redis_client.set_json", _set_json_noop)
    monkeypatch.setattr("app.core.redis_client.get_json", _get_json_noop)


def pytest_configure(config) -> None:  # noqa: ANN001
    """Reset cached settings singleton so optional env overrides during collection apply."""

    from app.core.config import get_settings
    from app.models import load_all_models

    load_all_models()
    get_settings.cache_clear()

