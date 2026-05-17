"""Fernet helpers for ``operator_external_apis.ciphertext`` rows."""

from __future__ import annotations

import json
from typing import Any

from app.core.symmetric_fernet import hive_fernet


def encrypt_credentials_blob(payload: dict[str, Any]) -> str:
    """Serialize credentials as sorted JSON and encrypt."""

    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hive_fernet().encrypt(raw).decode("utf-8")


def decrypt_credentials_blob(ciphertext: str) -> dict[str, Any]:
    """Decrypt ciphertext into a JSON object."""

    blob = hive_fernet().decrypt(ciphertext.encode("utf-8"))
    data = json.loads(blob.decode("utf-8"))
    if not isinstance(data, dict):
        msg = "credentials payload must be a JSON object"
        raise ValueError(msg)
    return data


__all__ = ["decrypt_credentials_blob", "encrypt_credentials_blob"]
