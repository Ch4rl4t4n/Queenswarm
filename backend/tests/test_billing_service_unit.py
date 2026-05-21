from __future__ import annotations

from types import SimpleNamespace

from app.application.services.billing import evaluate_usage_health, resolve_plan_features, resolve_plan_limits


def test_resolve_plan_limits_when_free_tier_then_expected_defaults() -> None:
    subscription = SimpleNamespace(
        tier="free",
        limits_override={},
    )
    limits = resolve_plan_limits(subscription)  # type: ignore[arg-type]
    assert limits["monthly_supervisor_sessions_hard"] == 80
    assert limits["monthly_token_hard"] == 250_000
    assert limits["max_agents_hard"] == 2
    assert limits["max_swarms_hard"] == 1


def test_resolve_plan_features_when_override_present_then_override_applied() -> None:
    subscription = SimpleNamespace(
        tier="pro",
        feature_overrides={"priority_support": True},
    )
    features = resolve_plan_features(subscription)  # type: ignore[arg-type]
    assert features["advanced_routines"] is True
    assert features["priority_support"] is True


def test_evaluate_usage_health_when_value_over_soft_then_soft_flagged() -> None:
    limits = {
        "monthly_token_soft": 100,
        "monthly_token_hard": 200,
        "monthly_supervisor_sessions_soft": 10,
        "monthly_supervisor_sessions_hard": 20,
        "monthly_external_calls_soft": 5,
        "monthly_external_calls_hard": 10,
        "storage_mb_soft": 50,
        "storage_mb_hard": 100,
    }
    usage = {
        "monthly_tokens": 120.0,
        "monthly_supervisor_sessions": 4.0,
        "monthly_external_calls": 2.0,
        "storage_mb_estimate": 10.0,
    }
    health = evaluate_usage_health(limits=limits, usage=usage)
    assert health["monthly_tokens"]["soft_exceeded"] is True
    assert health["monthly_tokens"]["hard_exceeded"] is False
