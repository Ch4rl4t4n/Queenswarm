"""Unit tests for Polymarket L2 and Kalshi RSA signing helpers."""

from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from app.application.services.prediction_market_auth import (
    build_kalshi_rsa_headers,
    build_polymarket_l2_headers,
    kalshi_rsa_secrets_configured,
    kalshi_sign_path,
    polymarket_l2_secrets_configured,
)


def test_polymarket_l2_secrets_configured_requires_all_fields() -> None:
    """All four Polymarket L2 fields must be present."""

    assert polymarket_l2_secrets_configured(
        {
            "polymarket_api_key": "k",
            "polymarket_api_secret": "s",
            "polymarket_api_passphrase": "p",
            "polymarket_wallet_address": "0xabc",
        },
    )
    assert not polymarket_l2_secrets_configured({"polymarket_api_key": "k"})


def test_build_polymarket_l2_headers_shape() -> None:
    """Polymarket headers include required POLY_* keys."""

    headers = build_polymarket_l2_headers(
        method="GET",
        request_path="/data/orders",
        body="",
        secrets={
            "polymarket_api_key": "key-1",
            "polymarket_api_secret": "c2VjcmV0",  # base64 url-safe secret
            "polymarket_api_passphrase": "pass",
            "polymarket_wallet_address": "0xdeadbeef",
        },
    )
    assert headers["POLY_API_KEY"] == "key-1"
    assert headers["POLY_PASSPHRASE"] == "pass"
    assert headers["POLY_ADDRESS"] == "0xdeadbeef"
    assert headers["POLY_TIMESTAMP"].isdigit()
    assert len(headers["POLY_SIGNATURE"]) > 8


def test_kalshi_sign_path_includes_trade_api_prefix() -> None:
    """Kalshi signing path must include /trade-api/v2 prefix."""

    signed = kalshi_sign_path(
        base_url="https://api.elections.kalshi.com/trade-api/v2",
        resolved_path="/portfolio/balance",
    )
    assert signed == "/trade-api/v2/portfolio/balance"


def test_build_kalshi_rsa_headers_shape() -> None:
    """Kalshi headers include access key, timestamp, signature."""

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    assert kalshi_rsa_secrets_configured(
        {"kalshi_api_key_id": "key-id", "kalshi_private_key_pem": pem},
    )

    headers = build_kalshi_rsa_headers(
        method="GET",
        sign_path="/trade-api/v2/portfolio/balance",
        secrets={"kalshi_api_key_id": "key-id", "kalshi_private_key_pem": pem},
    )
    assert headers["KALSHI-ACCESS-KEY"] == "key-id"
    assert headers["KALSHI-ACCESS-TIMESTAMP"].isdigit()
    assert len(headers["KALSHI-ACCESS-SIGNATURE"]) > 16
