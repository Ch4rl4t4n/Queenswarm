"""Unit guards for scripted dashboard API key formatting helpers."""

from __future__ import annotations

import uuid

import pytest

from app.services.dashboard_api_keys import (
    build_plaintext_api_key,
    normalize_api_key_source_name,
    parse_api_key_token,
)


def test_parse_api_key_token_roundtrips_stable_uuid_slug() -> None:
    kid = uuid.uuid4()
    raw = build_plaintext_api_key(kid)
    parsed = parse_api_key_token(raw)
    assert parsed is not None
    assert parsed[0] == kid


def test_parse_api_key_token_rejects_garbage() -> None:
    assert parse_api_key_token("jwt-like.token.value") is None
    assert parse_api_key_token("qs_kw_deadbeef.invalid") is None


def test_normalize_api_key_source_name_slugifies() -> None:
    assert normalize_api_key_source_name("  CI / Staging  ") == "ci_staging"
    assert normalize_api_key_source_name("vscode-extension") == "vscode-extension"


def test_normalize_api_key_source_name_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        normalize_api_key_source_name("!")
    with pytest.raises(ValueError):
        normalize_api_key_source_name("ab--c")
