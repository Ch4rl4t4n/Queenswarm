"""bcrypt hashing + RFC 6238 TOTP helpers for dashboard operators."""

from __future__ import annotations

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
