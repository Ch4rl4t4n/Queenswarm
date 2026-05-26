"""Unit tests for Proof-of-Hive verify receipts."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from app.application.services.proof_of_hive import (
    build_proof_share_url,
    mint_proof_token,
    mint_publish_proof_receipt,
    verify_proof_public,
    verify_proof_token,
)


def test_mint_and_verify_roundtrip() -> None:
    payload = {
        "v": 1,
        "artifact_type": "publish_pack",
        "artifact_id": str(uuid.uuid4()),
        "title": "Test pack",
        "trust_lane": "simulate",
        "verified_at": "2026-05-22T08:00:00Z",
        "event_kind": "queue_approved",
    }
    with patch("app.application.services.proof_of_hive.settings") as mock_settings:
        mock_settings.secret_key = "test-secret-key-min-32-chars-long"
        mock_settings.proof_of_hive_signing_secret = ""
        token = mint_proof_token(payload=payload)
        decoded = verify_proof_token(token)
    assert decoded is not None
    assert decoded["title"] == "Test pack"


def test_verify_rejects_tampered_token() -> None:
    with patch("app.application.services.proof_of_hive.settings") as mock_settings:
        mock_settings.secret_key = "test-secret-key-min-32-chars-long"
        mock_settings.proof_of_hive_signing_secret = ""
        token = mint_proof_token(payload={"v": 1, "artifact_type": "publish_pack", "artifact_id": "x", "title": "t", "trust_lane": "auto", "verified_at": "z"})
        bad = token[:-4] + "xxxx"
        assert verify_proof_token(bad) is None


def test_mint_publish_proof_receipt() -> None:
    with patch("app.application.services.proof_of_hive.settings") as mock_settings:
        mock_settings.proof_of_hive_enabled = True
        mock_settings.secret_key = "test-secret-key-min-32-chars-long"
        mock_settings.proof_of_hive_signing_secret = ""
        mock_settings.domain = "queenswarm.love"
        receipt = mint_publish_proof_receipt(
            deliverable_id=uuid.uuid4(),
            title="Morning post",
            kind="social_simulate",
            channel="instagram",
        )
    assert receipt is not None
    assert receipt.trust_lane == "simulate"
    assert "/proof/" in receipt.share_url


def test_verify_proof_public_valid() -> None:
    with patch("app.application.services.proof_of_hive.settings") as mock_settings:
        mock_settings.proof_of_hive_enabled = True
        mock_settings.secret_key = "test-secret-key-min-32-chars-long"
        mock_settings.proof_of_hive_signing_secret = ""
        mock_settings.domain = "queenswarm.love"
        token = mint_proof_token(
            payload={
                "v": 1,
                "artifact_type": "publish_pack",
                "artifact_id": str(uuid.uuid4()),
                "title": "Pack",
                "trust_lane": "live",
                "verified_at": "2026-05-22T08:00:00Z",
                "event_kind": "social_live",
            },
        )
        view = verify_proof_public(token)
    assert view.valid is True
    assert view.trust_lane == "live"


def test_build_proof_share_url() -> None:
    with patch("app.application.services.proof_of_hive.settings") as mock_settings:
        mock_settings.domain = "queenswarm.love"
        url = build_proof_share_url("abc.def")
    assert url == "https://queenswarm.love/proof/abc.def"
