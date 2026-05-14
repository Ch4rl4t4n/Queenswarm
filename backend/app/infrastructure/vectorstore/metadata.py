"""Shared metadata flattening for vector payloads (Chroma + Qdrant)."""

from __future__ import annotations

import json
from typing import Any


def flatten_vector_metadata(metadata: dict[str, Any] | None) -> dict[str, str | int | float | bool]:
    """Normalize arbitrary metadata into scalar-only maps safe for Chroma / Qdrant payloads."""

    if not metadata:
        return {}
    safe: dict[str, str | int | float | bool] = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            safe[str(key)] = value
        else:
            safe[str(key)] = json.dumps(value, default=str)
    return safe
