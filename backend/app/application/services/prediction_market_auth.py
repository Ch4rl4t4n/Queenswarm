"""Signed HTTP auth for Polymarket CLOB (L2 HMAC) and Kalshi (RSA-PSS)."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import urlparse

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

POLYMARKET_L2_AUTH = "polymarket_l2"
KALSHI_RSA_AUTH = "kalshi_rsa"


def polymarket_l2_secrets_configured(payload: dict[str, Any]) -> bool:
    """Return True when Polymarket L2 credential bundle is complete."""

    required = (
        "polymarket_api_key",
        "polymarket_api_secret",
        "polymarket_api_passphrase",
        "polymarket_wallet_address",
    )
    return all(isinstance(payload.get(key), str) and str(payload[key]).strip() for key in required)


def kalshi_rsa_secrets_configured(payload: dict[str, Any]) -> bool:
    """Return True when Kalshi RSA credential bundle is complete."""

    key_id = payload.get("kalshi_api_key_id")
    pem = payload.get("kalshi_private_key_pem")
    return isinstance(key_id, str) and bool(key_id.strip()) and isinstance(pem, str) and "BEGIN" in pem


def _polymarket_decode_secret(secret: str) -> bytes:
    """Decode Polymarket API secret (URL-safe base64)."""

    raw = secret.strip()
    pad = "=" * (-len(raw) % 4)
    try:
        return base64.urlsafe_b64decode(raw + pad)
    except (ValueError, binascii.Error):
        return raw.encode("utf-8")


def build_polymarket_l2_headers(
    *,
    method: str,
    request_path: str,
    body: str,
    secrets: dict[str, Any],
) -> dict[str, str]:
    """Build Polymarket CLOB L2 authentication headers."""

    api_key = str(secrets.get("polymarket_api_key") or "").strip()
    api_secret = str(secrets.get("polymarket_api_secret") or "").strip()
    passphrase = str(secrets.get("polymarket_api_passphrase") or "").strip()
    address = str(secrets.get("polymarket_wallet_address") or "").strip()
    if not all((api_key, api_secret, passphrase, address)):
        msg = "Polymarket L2 credentials incomplete."
        raise ValueError(msg)

    timestamp = str(int(time.time()))
    path_only = request_path.split("?", 1)[0]
    message = f"{timestamp}{method.upper()}{path_only}{body}"
    secret_bytes = _polymarket_decode_secret(api_secret)
    digest = hmac.new(secret_bytes, message.encode("utf-8"), hashlib.sha256).digest()
    signature = base64.urlsafe_b64encode(digest).decode("utf-8")

    return {
        "POLY_ADDRESS": address,
        "POLY_API_KEY": api_key,
        "POLY_PASSPHRASE": passphrase,
        "POLY_TIMESTAMP": timestamp,
        "POLY_SIGNATURE": signature,
    }


def kalshi_sign_path(*, base_url: str, resolved_path: str) -> str:
    """Return Kalshi path segment used for RSA signing (includes /trade-api/v2 prefix)."""

    parsed = urlparse(base_url.strip())
    base_path = (parsed.path or "").rstrip("/")
    rel = resolved_path.split("?", 1)[0]
    if not rel.startswith("/"):
        rel = f"/{rel}"
    if base_path and rel.startswith(base_path):
        return rel
    return f"{base_path}{rel}" if base_path else rel


def build_kalshi_rsa_headers(
    *,
    method: str,
    sign_path: str,
    secrets: dict[str, Any],
) -> dict[str, str]:
    """Build Kalshi RSA-PSS request headers."""

    key_id = str(secrets.get("kalshi_api_key_id") or "").strip()
    pem = str(secrets.get("kalshi_private_key_pem") or "").strip()
    if not key_id or not pem:
        msg = "Kalshi RSA credentials incomplete."
        raise ValueError(msg)

    timestamp = str(int(time.time() * 1000))
    path_only = sign_path.split("?", 1)[0]
    message = f"{timestamp}{method.upper()}{path_only}".encode("utf-8")

    private_key = serialization.load_pem_private_key(pem.encode("utf-8"), password=None)
    signature = private_key.sign(
        message,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
        hashes.SHA256(),
    )
    return {
        "KALSHI-ACCESS-KEY": key_id,
        "KALSHI-ACCESS-TIMESTAMP": timestamp,
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode("utf-8"),
    }


def augment_prediction_market_headers(
    *,
    auth_type: str,
    secrets: dict[str, Any],
    method: str,
    base_url: str,
    resolved_path: str,
    body: dict[str, Any] | None,
) -> dict[str, str]:
    """Attach venue-specific signed headers for outbound connector calls."""

    style = auth_type.strip().lower()
    if style == POLYMARKET_L2_AUTH:
        body_text = json.dumps(body, separators=(",", ":"), sort_keys=True) if body else ""
        return build_polymarket_l2_headers(
            method=method,
            request_path=resolved_path,
            body=body_text,
            secrets=secrets,
        )
    if style == KALSHI_RSA_AUTH:
        sign_path = kalshi_sign_path(base_url=base_url, resolved_path=resolved_path)
        return build_kalshi_rsa_headers(method=method, sign_path=sign_path, secrets=secrets)
    return {}


__all__ = [
    "KALSHI_RSA_AUTH",
    "POLYMARKET_L2_AUTH",
    "augment_prediction_market_headers",
    "build_kalshi_rsa_headers",
    "build_polymarket_l2_headers",
    "kalshi_rsa_secrets_configured",
    "kalshi_sign_path",
    "polymarket_l2_secrets_configured",
]
