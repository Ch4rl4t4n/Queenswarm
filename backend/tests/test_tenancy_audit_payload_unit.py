"""Unit tests for tenant audit payload enrichment."""

from __future__ import annotations

from app.application.services.tenancy import enrich_audit_payload


def test_enrich_audit_payload_adds_ip_when_missing() -> None:
    merged = enrich_audit_payload({"source": "self-service"}, client_ip="10.0.0.42")
    assert merged["ip"] == "10.0.0.42"
    assert merged["source"] == "self-service"


def test_enrich_audit_payload_preserves_existing_ip() -> None:
    merged = enrich_audit_payload({"ip": "192.168.1.1"}, client_ip="10.0.0.42")
    assert merged["ip"] == "192.168.1.1"


def test_enrich_audit_payload_skips_blank_ip() -> None:
    merged = enrich_audit_payload({"action": "x"}, client_ip=None)
    assert "ip" not in merged
