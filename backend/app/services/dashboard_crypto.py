"""bcrypt hashing + RFC 6238 TOTP helpers for dashboard operators."""

from __future__ import annotations

import secrets

import pyotp
from passlib.context import CryptContext

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_dashboard_password(password: str) -> str:
    """Return salted bcrypt digest suitable for Postgres ``dashboard_users.password_hash``."""

    return _pwd_ctx.hash(password)


def verify_dashboard_password(password: str, hashed: str) -> bool:
    """Return True when the supplied password validates against stored bcrypt."""

    return _pwd_ctx.verify(password, hashed)


def mint_totp_secret() -> str:
    """Produce a Base32-encoded TOTP seed for provisioning authenticator apps."""

    return pyotp.random_base32()


def totp_verify(secret: str, code: str) -> bool:
    """Validate a 6-digit (or configurable) OTP with ±1 drift window."""

    cleaned = "".join(code.split())
    if not cleaned:
        return False
    return bool(pyotp.TOTP(secret).verify(cleaned, valid_window=1))


def totp_uri_for_email(*, issuer: str, email: str, secret: str) -> str:
    """Return ``otpauth://`` URI consumed by QR encoders."""

    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def mint_plain_backup_codes(*, count: int = 8) -> list[str]:
    """Return human-readable one-time backup codes (uppercase, unambiguous alphabet)."""

    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return ["".join(secrets.choice(alphabet) for _ in range(8)) for _ in range(count)]


def backup_codes_hashed(plain: list[str]) -> list[str]:
    """Hash backup codes for JSON storage (bcrypt via existing dashboard context)."""

    return [hash_dashboard_password(c.strip().upper()) for c in plain if c.strip()]


def consume_matching_backup_code(hashes: list[str], code: str) -> list[str] | None:
    """Remove the first matching backup hash; return updated list or None if no match."""

    normalized = code.strip().upper().replace(" ", "")
    if not normalized:
        return None
    for i, h in enumerate(hashes):
        try:
            if verify_dashboard_password(normalized, h):
                return hashes[:i] + hashes[i + 1 :]
        except ValueError:
            continue
    return None
