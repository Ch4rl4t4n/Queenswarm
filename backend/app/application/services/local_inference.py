"""Track M — Local sovereign inference (Ollama / vLLM OpenAI-compatible)."""

from __future__ import annotations

from typing import Any, Literal

import httpx
import structlog
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings

logger = structlog.get_logger(__name__)

LocalProvider = Literal["ollama", "vllm"]


class LocalInferencePingOut(BaseModel):
    """Health check for one local provider."""

    model_config = ConfigDict(extra="ignore")

    provider: LocalProvider
    ok: bool
    endpoint: str
    model_count: int = 0
    message: str = ""


class LocalInferenceStatusOut(BaseModel):
    """Deployment + tenant local inference snapshot."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    llm_airgap: bool
    ollama_api_base: str
    ollama_default_model: str
    vllm_api_base: str
    vllm_default_model: str
    configured_models: list[str] = Field(default_factory=list)
    pings: list[LocalInferencePingOut] = Field(default_factory=list)


def is_local_inference_model(model_name: str) -> bool:
    """Return True when the slug routes to Ollama or tenant vLLM base."""

    lowered = model_name.lower().strip()
    if lowered.startswith("ollama/"):
        return True
    if settings.vllm_api_base.strip() and lowered.startswith("openai/"):
        return resolve_vllm_model_slug() == lowered
    return False


def is_cloud_inference_model(model_name: str) -> bool:
    """Return True for external paid providers (blocked when LLM_AIRGAP=1)."""

    return not is_local_inference_model(model_name)


def resolve_ollama_model_slug() -> str:
    """Canonical default Ollama LiteLLM slug."""

    raw = settings.ollama_default_model.strip()
    if raw.startswith("ollama/"):
        return raw
    return f"ollama/{raw.removeprefix('ollama/')}" if raw else "ollama/qwen2.5:7b"


def resolve_vllm_model_slug() -> str:
    """Canonical vLLM OpenAI-compatible slug."""

    return settings.vllm_default_model.strip() or "openai/local-model"


def configured_local_model_slugs() -> list[str]:
    """Ordered local model slugs when deployment local LLM is enabled."""

    if not settings.local_llm_enabled:
        return []
    slugs: list[str] = []
    if settings.ollama_api_base.strip():
        slugs.append(resolve_ollama_model_slug())
    if settings.vllm_api_base.strip():
        slugs.append(resolve_vllm_model_slug())
    return slugs


def assert_model_allowed_when_airgap(model_name: str) -> None:
    """Raise when LLM_AIRGAP blocks a cloud hop."""

    if not settings.llm_airgap:
        return
    if is_cloud_inference_model(model_name):
        msg = (
            f"LLM_AIRGAP=1 blocks cloud model `{model_name}`. "
            f"Use local_sovereign routing with Ollama ({settings.ollama_api_base}) "
            f"or disable LLM_AIRGAP."
        )
        raise RuntimeError(msg)


def enrich_litellm_completion_kwargs(kwargs: dict[str, Any], model_name: str) -> dict[str, Any]:
    """Attach api_base / dummy key for local providers."""

    lowered = model_name.lower()
    if lowered.startswith("ollama/"):
        kwargs["api_base"] = settings.ollama_api_base.rstrip("/")
        kwargs["api_key"] = "ollama"
        return kwargs
    if settings.vllm_api_base.strip() and lowered == resolve_vllm_model_slug().lower():
        base = settings.vllm_api_base.rstrip("/")
        kwargs["api_base"] = base if base.endswith("/v1") else f"{base}/v1"
        kwargs["api_key"] = kwargs.get("api_key") or "local-vllm"
    return kwargs


async def ping_ollama(*, timeout_sec: float = 5.0) -> LocalInferencePingOut:
    """GET /api/tags from Ollama."""

    endpoint = settings.ollama_api_base.rstrip("/")
    url = f"{endpoint}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
        models = payload.get("models") if isinstance(payload, dict) else []
        count = len(models) if isinstance(models, list) else 0
        return LocalInferencePingOut(
            provider="ollama",
            ok=True,
            endpoint=endpoint,
            model_count=count,
            message=f"Ollama reachable — {count} model(s) listed.",
        )
    except httpx.HTTPError as exc:
        logger.warning("local_inference.ollama_ping_failed", endpoint=endpoint, error=str(exc))
        return LocalInferencePingOut(
            provider="ollama",
            ok=False,
            endpoint=endpoint,
            message=f"Ollama ping failed: {exc}",
        )


async def ping_vllm(*, timeout_sec: float = 5.0) -> LocalInferencePingOut | None:
    """GET /v1/models from vLLM when configured."""

    base = settings.vllm_api_base.strip()
    if not base:
        return None
    root = base.rstrip("/")
    url = f"{root}/models" if root.endswith("/v1") else f"{root}/v1/models"
    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else []
        count = len(data) if isinstance(data, list) else 0
        return LocalInferencePingOut(
            provider="vllm",
            ok=True,
            endpoint=root,
            model_count=count,
            message=f"vLLM reachable — {count} model(s) listed.",
        )
    except httpx.HTTPError as exc:
        logger.warning("local_inference.vllm_ping_failed", endpoint=root, error=str(exc))
        return LocalInferencePingOut(
            provider="vllm",
            ok=False,
            endpoint=root,
            message=f"vLLM ping failed: {exc}",
        )


async def compose_local_inference_status(*, run_ping: bool = False) -> LocalInferenceStatusOut:
    """Build operator status payload."""

    slugs = configured_local_model_slugs()
    pings: list[LocalInferencePingOut] = []
    if run_ping and settings.local_llm_enabled:
        pings.append(await ping_ollama())
        vllm_ping = await ping_vllm()
        if vllm_ping is not None:
            pings.append(vllm_ping)
    return LocalInferenceStatusOut(
        enabled=settings.local_llm_enabled,
        llm_airgap=settings.llm_airgap,
        ollama_api_base=settings.ollama_api_base,
        ollama_default_model=resolve_ollama_model_slug(),
        vllm_api_base=settings.vllm_api_base,
        vllm_default_model=resolve_vllm_model_slug(),
        configured_models=slugs,
        pings=pings,
    )


__all__ = [
    "LocalInferencePingOut",
    "LocalInferenceStatusOut",
    "assert_model_allowed_when_airgap",
    "compose_local_inference_status",
    "configured_local_model_slugs",
    "enrich_litellm_completion_kwargs",
    "is_cloud_inference_model",
    "is_local_inference_model",
    "ping_ollama",
    "ping_vllm",
    "resolve_ollama_model_slug",
    "resolve_vllm_model_slug",
]
