"""Connector vault cryptography helpers."""

from __future__ import annotations

import json

import pytest
from cryptography.fernet import Fernet

from app.infrastructure.connectors.secure_vault import (
    CredentialPayload,
    build_connector_vault_cipher,
)


def test_credential_payload_to_envelope_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    """API keys surface as Bearer headers for downstream HTTP."""

    monkeypatch.delenv("CONNECTOR_VAULT_FERNET_KEY", raising=False)

    blob = CredentialPayload(kind="api_key", api_key="hive-secret-example")
    env = blob.to_envelope()
    hdr = env.bearer_header()
    assert hdr["Authorization"].endswith("hive-secret-example")


def test_derived_fernet_can_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    """HKDF derivation path unlocks payloads when Fernet env key absent."""

    monkeypatch.delenv("CONNECTOR_VAULT_FERNET_KEY", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("SECRET_KEY", "secret-key-derived-from-tests-min-length-hex")
    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    cipher = build_connector_vault_cipher(settings)
    raw = {"kind": "oauth2", "oauth2_access_token": "token-123"}
    token = cipher.encrypt(json.dumps(raw).encode("utf-8"))
    opened = json.loads(cipher.decrypt(token).decode("utf-8"))
    assert opened["oauth2_access_token"] == "token-123"
    restored = CredentialPayload.model_validate(opened)
    assert restored.to_envelope().bearer_header()["Authorization"].endswith("token-123")
    get_settings.cache_clear()


def test_explicit_connector_fernet_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Static Fernet envelope matches operator-supplied rotations."""

    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("CONNECTOR_VAULT_FERNET_KEY", key)
    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    cipher = build_connector_vault_cipher(settings)
    payload = CredentialPayload(kind="api_key", api_key="k")
    tok = cipher.encrypt(json.dumps(payload.model_dump(mode="json")).encode("utf-8"))
    assert CredentialPayload.model_validate(json.loads(cipher.decrypt(tok).decode("utf-8"))).api_key == "k"
    get_settings.cache_clear()
