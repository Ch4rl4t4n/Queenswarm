"""Unit coverage for hive tier resolution helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.hive_tier import (
    FIXED_ORCHESTRATOR_AGENT_NAME,
    is_fixed_orchestrator_agent,
    normalize_output_config_hive_tier,
    resolve_hive_tier,
)


def test_is_fixed_orchestrator_by_name() -> None:
    agent = SimpleNamespace(name=FIXED_ORCHESTRATOR_AGENT_NAME, config={})
    assert is_fixed_orchestrator_agent(agent) is True


def test_is_fixed_orchestrator_by_hive_fixed_flag() -> None:
    agent = SimpleNamespace(name="Worker-1", config={"hive_fixed": True})
    assert is_fixed_orchestrator_agent(agent) is True


def test_is_fixed_orchestrator_by_tier_config() -> None:
    agent = SimpleNamespace(name="Bee", config={"hive_tier": "Orchestrator"})
    assert is_fixed_orchestrator_agent(agent) is True


def test_is_not_fixed_orchestrator_for_worker() -> None:
    agent = SimpleNamespace(name="Scraper-2", config={"hive_tier": "worker"})
    assert is_fixed_orchestrator_agent(agent) is False


@pytest.mark.parametrize(
    ("output_config", "expected"),
    [
        (None, None),
        ({}, None),
        ({"hive_tier": "  manager  "}, "manager"),
        ({"hive_tier": ""}, None),
        ({"hive_tier": 42}, None),
    ],
)
def test_normalize_output_config_hive_tier(output_config: dict | None, expected: str | None) -> None:
    assert normalize_output_config_hive_tier(output_config) == expected


def test_resolve_hive_tier_orchestrator_wins_over_config() -> None:
    agent = SimpleNamespace(name=FIXED_ORCHESTRATOR_AGENT_NAME, config={})
    cfg = SimpleNamespace(output_config={"hive_tier": "worker"})
    assert resolve_hive_tier(agent=agent, agent_config=cfg) == "orchestrator"


def test_resolve_hive_tier_from_agent_config() -> None:
    agent = SimpleNamespace(name="Manager-1", config={})
    cfg = SimpleNamespace(output_config={"hive_tier": "manager"})
    assert resolve_hive_tier(agent=agent, agent_config=cfg) == "manager"


def test_resolve_hive_tier_without_config() -> None:
    agent = SimpleNamespace(name="Worker-9", config={})
    assert resolve_hive_tier(agent=agent, agent_config=None) is None
