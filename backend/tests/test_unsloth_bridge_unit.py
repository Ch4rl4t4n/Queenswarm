"""Unit tests for Track M LOC7 Unsloth bridge helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.application.services.unsloth_bridge_service import (
    UnslothBridgeValidateIn,
    build_gguf_modelfile,
    build_unsloth_bridge_plan,
    litellm_slug_from_ollama_tag,
    normalize_ollama_model_name,
)


def test_normalize_ollama_model_name() -> None:
    assert normalize_ollama_model_name("Queenswarm Tenant V1") == "queenswarm-tenant-v1"


def test_litellm_slug_from_ollama_tag() -> None:
    assert litellm_slug_from_ollama_tag("queenswarm-tenant-v1") == "ollama/queenswarm-tenant-v1"


def test_build_gguf_modelfile(tmp_path: Path) -> None:
    gguf = tmp_path / "model.gguf"
    gguf.write_bytes(b"fake")
    body = build_gguf_modelfile(gguf_path=gguf, system_prompt="You are a sovereign assistant.")
    assert str(gguf.resolve()) in body
    assert "sovereign assistant" in body


def test_build_unsloth_bridge_plan(tmp_path: Path) -> None:
    gguf = tmp_path / "adapter.gguf"
    gguf.write_bytes(b"fake")
    plan = build_unsloth_bridge_plan(
        UnslothBridgeValidateIn(name="My Adapter", gguf_path=str(gguf), base_model="qwen2.5:7b"),
    )
    assert plan.ollama_tag == "my-adapter"
    assert plan.litellm_slug == "ollama/my-adapter"
    assert "ADAPTER" in plan.modelfile_body


def test_build_unsloth_bridge_plan_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        build_unsloth_bridge_plan(
            UnslothBridgeValidateIn(name="ab", gguf_path="/nonexistent/model.gguf"),
        )
