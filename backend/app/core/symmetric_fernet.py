"""Symmetric Fernet keyed from ``settings.secret_key`` (same derivation as LLM vault)."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def hive_fernet() -> Fernet:
    """Derive URL-safe Fernet key from JWT secret."""

    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


__all__ = ["hive_fernet"]
