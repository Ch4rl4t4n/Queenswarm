"""Vector metadata flattening for Qdrant / Chroma payloads."""

from __future__ import annotations

from app.infrastructure.vectorstore.metadata import flatten_vector_metadata


def test_flatten_vector_metadata_preserves_scalars() -> None:
    """Scalars pass through unchanged."""

    out = flatten_vector_metadata({"n": 3, "f": 1.5, "s": "x", "b": True})
    assert out == {"n": 3, "f": 1.5, "s": "x", "b": True}


def test_flatten_vector_metadata_json_encodes_nested() -> None:
    """Nested structures stringify for vector payload safety."""

    out = flatten_vector_metadata({"nested": {"k": "v"}})
    assert isinstance(out["nested"], str)
    assert "k" in out["nested"]
