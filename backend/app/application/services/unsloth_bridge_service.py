"""Track M LOC7 — Unsloth → Ollama bridge helpers (Modelfile + slug normalization)."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

_OLLAMA_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,62}$")


class UnslothBridgePlanOut(BaseModel):
    """Operator plan for importing a GGUF/LoRA artifact into Ollama."""

    model_config = ConfigDict(extra="forbid")

    ollama_tag: str
    litellm_slug: str
    gguf_path: str
    modelfile_body: str
    ollama_create_command: str
    register_hint: str = ""


class UnslothBridgeValidateIn(BaseModel):
    """Validate bridge inputs before Ollama import."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=64)
    gguf_path: str = Field(min_length=1, max_length=512)
    base_model: str = Field(default="", max_length=128)
    system_prompt: str = Field(default="", max_length=4000)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        normalized = normalize_ollama_model_name(value)
        if not _OLLAMA_NAME_RE.match(normalized):
            msg = "Model name must be lowercase alphanumeric with . _ - only."
            raise ValueError(msg)
        return normalized


def normalize_ollama_model_name(name: str) -> str:
    """Normalize operator-provided Ollama model tag."""

    lowered = name.strip().lower().replace(" ", "-")
    lowered = re.sub(r"[^a-z0-9._-]+", "-", lowered)
    lowered = re.sub(r"-{2,}", "-", lowered).strip("-")
    return lowered or "queenswarm-adapter"


def litellm_slug_from_ollama_tag(tag: str) -> str:
    """Canonical LiteLLM slug for a local Ollama tag."""

    clean = tag.removeprefix("ollama/").strip()
    return f"ollama/{clean}" if clean else "ollama/queenswarm-adapter"


def build_gguf_modelfile(
    *,
    gguf_path: Path,
    base_model: str = "",
    system_prompt: str = "",
) -> str:
    """Build Ollama Modelfile body for a GGUF export from Unsloth Studio."""

    resolved = gguf_path.expanduser().resolve()
    from_line = f"FROM {resolved}"
    if base_model.strip():
        from_line = f"FROM {base_model.strip()}\nADAPTER {resolved}"
    lines = [from_line]
    prompt = system_prompt.strip()
    if prompt:
        lines.append(f'SYSTEM """{prompt}"""')
    lines.append('TEMPLATE """{{ .System }}\n{{ .Prompt }}"""')
    return "\n".join(lines) + "\n"


def build_unsloth_bridge_plan(payload: UnslothBridgeValidateIn) -> UnslothBridgePlanOut:
    """Compose Modelfile + Ollama create command for operator script."""

    gguf = Path(payload.gguf_path)
    if not gguf.is_file():
        msg = f"GGUF/adapter file not found: {gguf}"
        raise FileNotFoundError(msg)

    modelfile = build_gguf_modelfile(
        gguf_path=gguf,
        base_model=payload.base_model,
        system_prompt=payload.system_prompt,
    )
    tag = normalize_ollama_model_name(payload.name)
    slug = litellm_slug_from_ollama_tag(tag)
    create_cmd = f'ollama create "{tag}" -f "<modelfile>"'
    return UnslothBridgePlanOut(
        ollama_tag=tag,
        litellm_slug=slug,
        gguf_path=str(gguf.resolve()),
        modelfile_body=modelfile,
        ollama_create_command=create_cmd,
        register_hint=(
            f"Register in Queenswarm: POST /api/v1/llm-routing/local-adapters "
            f'with ollama_tag="{tag}" and litellm_slug="{slug}".'
        ),
    )


__all__ = [
    "UnslothBridgePlanOut",
    "UnslothBridgeValidateIn",
    "build_gguf_modelfile",
    "build_unsloth_bridge_plan",
    "litellm_slug_from_ollama_tag",
    "normalize_ollama_model_name",
]
