"""Unit tests for Grok Control Plane policy and guardrails helpers."""

from __future__ import annotations

from datetime import UTC, timedelta

import pytest

from app.application.services import grok_control_plane as service
from app.infrastructure.persistence.models.tenant import Tenant


@pytest.fixture
def grok_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable deterministic Grok CP settings for tests."""

    monkeypatch.setattr(service.settings, "grok_control_plane_enabled", True)
    monkeypatch.setattr(service.settings, "grok_cp_require_approval_for_risk", "medium,high,critical")
    monkeypatch.setattr(service.settings, "grok_cp_allow_prod_deploy", False)
    monkeypatch.setattr(service.settings, "grok_cp_deny_command_patterns", "rm -rf")
    monkeypatch.setattr(service.settings, "grok_cp_profile_read_only_commands", "git status --short,git diff --stat")
    monkeypatch.setattr(service.settings, "grok_cp_profile_ci_quick_commands", "git status --short,echo ok")
    monkeypatch.setattr(service.settings, "grok_cp_profile_deploy_candidate_commands", "echo dry-run")
    monkeypatch.setattr(service.settings, "grok_cp_profile_prod_deploy_commands", "echo deploy")
    monkeypatch.setattr(service.settings, "grok_cp_cli_enabled", False)
    monkeypatch.setattr(service.settings, "grok_cp_execute_commands", False)
    monkeypatch.setattr(service.settings, "grok_cp_repo_root", "/tmp")
    monkeypatch.setattr(service.settings, "grok_cp_dedup_hard_gate_enabled", True)
    monkeypatch.setattr(service.settings, "grok_cp_dedup_reuse_threshold", 0.62)
    monkeypatch.setattr(service.settings, "grok_cp_dedup_hybrid_threshold", 0.35)
    monkeypatch.setattr(service.settings, "grok_cp_cost_cap_usd_24h", 25.0)
    monkeypatch.setattr(
        service.settings,
        "grok_cp_estimated_cost_per_run",
        "read_only:0.03,code_edit:0.12,code_edit_and_test:0.30,deploy_candidate:0.55,prod_deploy:0.80",
    )
    monkeypatch.setattr(service.settings, "grok_cp_timeout_alert_threshold_24h", 3)
    monkeypatch.setattr(service.settings, "grok_cp_risk_escalation_threshold_24h", 6)
    monkeypatch.setattr(service.settings, "grok_cp_escalation_dedup_enabled", True)
    monkeypatch.setattr(service.settings, "grok_cp_escalation_cooldown_sec", 600)
    monkeypatch.setattr(service.settings, "grok_cp_last_resumed_marker_ttl_hours", 24)
    monkeypatch.setattr(
        service.settings,
        "grok_cp_dedup_min_score_by_source",
        "task:0.12,recipe:0.18,knowledge:0.16,grok_run:0.2",
    )
    monkeypatch.setattr(
        service.settings,
        "grok_cp_dedup_weight_by_source",
        "task:1.0,recipe:1.1,knowledge:0.95,grok_run:1.15",
    )


def test_requires_approval_when_risk_medium(grok_settings: None) -> None:
    cfg = service._policy_config()
    result = service._requires_approval(risk_level="medium", run_mode="code_edit", cfg=cfg)
    assert result is True


def test_requires_approval_when_deploy_candidate_even_low_risk(grok_settings: None) -> None:
    cfg = service._policy_config()
    result = service._requires_approval(risk_level="low", run_mode="deploy_candidate", cfg=cfg)
    assert result is True


def test_apply_command_policy_blocks_deny_pattern(grok_settings: None) -> None:
    cfg = service._policy_config()
    allowed = service._apply_command_policy("git status --short", cfg)
    blocked = service._apply_command_policy("rm -rf /tmp/work", cfg)
    assert allowed is True
    assert blocked is False


def test_safe_scope_paths_drops_parent_traversal(grok_settings: None) -> None:
    out = service._safe_scope_paths(["backend/app", "../etc/passwd", " frontend/components "])
    assert out == ["backend/app", "frontend/components"]


def test_dedup_config_clamps_hybrid_below_reuse(grok_settings: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service.settings, "grok_cp_dedup_reuse_threshold", 0.55)
    monkeypatch.setattr(service.settings, "grok_cp_dedup_hybrid_threshold", 0.7)
    cfg = service._dedup_config()
    assert cfg.reuse_threshold == 0.55
    assert cfg.hybrid_threshold < cfg.reuse_threshold


def test_parse_source_float_map_ignores_unknown_keys(grok_settings: None) -> None:
    parsed = service._parse_source_float_map(
        "task:0.3,unknown:0.9,grok_run:5.0",
        default={"task": 0.1, "grok_run": 0.2},
        low=0.0,
        high=1.0,
    )
    assert parsed["task"] == 0.3
    assert parsed["grok_run"] == 1.0


def test_artifact_confidence_and_priority_summary_succeeded(grok_settings: None) -> None:
    confidence, priority = service._artifact_confidence_and_priority(
        run_status="succeeded",
        artifact_kind="summary",
        text="A" * 1600,
    )
    assert confidence >= 0.86
    assert priority == "high"


def test_artifact_confidence_and_priority_command_log_failed(grok_settings: None) -> None:
    confidence, priority = service._artifact_confidence_and_priority(
        run_status="failed",
        artifact_kind="command_log",
        text="short",
    )
    assert confidence < 0.75
    assert priority in {"medium", "low"}


def test_apply_hivemind_review_tags_replaces_pending(grok_settings: None) -> None:
    tags = service._apply_hivemind_review_tags(
        ["priority-low", "hivemind-review-pending", "grok-output"],
        decision="approve",
    )
    assert "hivemind-review-pending" not in tags
    assert "hivemind-review-approved" in tags


def test_review_alert_timing_allowed_with_old_timestamp(grok_settings: None) -> None:
    tenant = Tenant(slug="demo", name="Demo", status="active", platform_mode="internal", operator_settings={})
    old = (service._utcnow() - timedelta(seconds=4000)).isoformat()
    tenant.operator_settings = {"execution_studio": {"grok_hivemind_review": {"last_alert_at": old}}}
    assert service._review_alert_timing_allowed(tenant=tenant, now=service._utcnow()) is True


def test_stamp_review_alert_sent_writes_operator_settings(grok_settings: None) -> None:
    tenant = Tenant(slug="demo", name="Demo", status="active", platform_mode="internal", operator_settings={})
    now = service._utcnow().replace(tzinfo=UTC)
    service._stamp_review_alert_sent(tenant=tenant, pending_count=14, now=now)
    studio = dict((tenant.operator_settings or {}).get("execution_studio") or {})
    bucket = dict(studio.get("grok_hivemind_review") or {})
    assert bucket.get("last_alert_pending_count") == 14
    assert isinstance(bucket.get("last_alert_at"), str)


def test_review_queue_escalation_reason_by_count(grok_settings: None) -> None:
    reason = service._review_queue_escalation_reason(
        pending_count=12,
        threshold=10,
        oldest_age_hours=2.0,
        age_threshold_hours=24,
    )
    assert reason is not None
    assert "count=12>=threshold=10" in reason


def test_review_queue_escalation_reason_by_age(grok_settings: None) -> None:
    reason = service._review_queue_escalation_reason(
        pending_count=2,
        threshold=10,
        oldest_age_hours=28.5,
        age_threshold_hours=24,
    )
    assert reason is not None
    assert "oldest_age_hours=28.5>=sla=24" in reason


def test_build_governance_snapshot_marks_breaches(grok_settings: None) -> None:
    out = service._build_governance_snapshot(
        mode_counts={"code_edit_and_test": 85},
        timeout_breaches=5,
        timeout_breaches_prev=1,
        high_risk_runs=8,
        high_risk_runs_prev=2,
        escalation_resumes_24h=4,
        escalation_resumes_prev_24h=1,
    )
    assert out.cost_cap_breached is True
    assert out.timeout_escalated is True
    assert out.risk_escalated is True
    assert out.escalation_resumes_24h == 4
    assert out.timeout_trend == "up"
    assert out.risk_trend == "up"
    assert out.resume_trend == "up"


def test_build_governance_snapshot_without_cap(grok_settings: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service.settings, "grok_cp_cost_cap_usd_24h", 0.0)
    out = service._build_governance_snapshot(
        mode_counts={"read_only": 10},
        timeout_breaches=0,
        timeout_breaches_prev=2,
        high_risk_runs=0,
        high_risk_runs_prev=1,
        escalation_resumes_24h=0,
        escalation_resumes_prev_24h=3,
    )
    assert out.cost_cap_breached is False
    assert out.cost_utilization == 0.0
    assert out.timeout_trend == "down"
    assert out.risk_trend == "down"
    assert out.resume_trend == "down"


def test_escalation_kind_from_metadata_normalizes(grok_settings: None) -> None:
    kind = service._escalation_kind_from_metadata({"escalation_kind": " Governance_Risk !! "})
    assert kind == "governance_risk"


def test_escalation_dedup_window_disabled(grok_settings: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service.settings, "grok_cp_escalation_dedup_enabled", False)
    assert service._escalation_dedup_window_sec() == 0


def test_stamp_and_read_last_resumed_escalation(grok_settings: None) -> None:
    tenant = Tenant(slug="demo", name="Demo", status="active", platform_mode="internal", operator_settings={})
    now = service._utcnow()
    run_id = service.uuid.uuid4()
    service._stamp_last_resumed_escalation(
        tenant,
        run_id=run_id,
        escalation_kind="governance_timeout",
        resumed_at=now,
    )
    out = service._read_last_resumed_escalation(tenant)
    assert out is not None
    assert out.run_id == str(run_id)
    assert out.escalation_kind == "governance_timeout"
    assert isinstance(out.remaining_ttl_hours, float)
    assert out.remaining_ttl_hours > 0.0


def test_read_last_resumed_escalation_respects_ttl(
    grok_settings: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant = Tenant(slug="demo", name="Demo", status="active", platform_mode="internal", operator_settings={})
    now = service._utcnow()
    run_id = service.uuid.uuid4()
    service._stamp_last_resumed_escalation(
        tenant,
        run_id=run_id,
        escalation_kind="review_queue_sla",
        resumed_at=now - timedelta(hours=26),
    )
    monkeypatch.setattr(service.settings, "grok_cp_last_resumed_marker_ttl_hours", 24)
    out = service._read_last_resumed_escalation(tenant)
    assert out is None


def test_count_recent_escalation_resumes(grok_settings: None) -> None:
    tenant = Tenant(slug="demo", name="Demo", status="active", platform_mode="internal", operator_settings={})
    now = service._utcnow()
    service._record_escalation_resume_event(
        tenant,
        run_id=service.uuid.uuid4(),
        escalation_kind="governance_cost",
        resumed_at=now - timedelta(hours=2),
    )
    service._record_escalation_resume_event(
        tenant,
        run_id=service.uuid.uuid4(),
        escalation_kind="governance_timeout",
        resumed_at=now - timedelta(hours=30),
    )
    assert service._count_recent_escalation_resumes(tenant, window_hours=24) == 1
