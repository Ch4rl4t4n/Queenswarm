"""LangFuse + OpenTelemetry bootstrap for LiteLLM and FastAPI hive traces."""

from __future__ import annotations

import os
from typing import Any

import litellm

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_observability_configured = False


def build_langfuse_metadata(
    *,
    agent_id: object | None = None,
    task_id: object | None = None,
    swarm_id: object | None = None,
    workflow_id: object | None = None,
    generation_name: str = "queenswarm-completion",
) -> dict[str, Any]:
    """Return LiteLLM metadata dict consumed by LangFuse success callbacks."""

    tags: list[str] = ["queenswarm"]
    if swarm_id:
        tags.append(f"swarm:{swarm_id}")
    if workflow_id:
        tags.append(f"workflow:{workflow_id}")

    metadata: dict[str, Any] = {
        "generation_name": generation_name,
        "trace_name": generation_name,
        "tags": tags,
    }
    if agent_id:
        metadata["trace_user_id"] = str(agent_id)
    session_parts = [str(p) for p in (task_id, swarm_id) if p]
    if session_parts:
        metadata["session_id"] = ":".join(session_parts)
    if task_id:
        metadata["trace_metadata"] = {"task_id": str(task_id)}
    if swarm_id:
        metadata.setdefault("trace_metadata", {})
        metadata["trace_metadata"]["swarm_id"] = str(swarm_id)
    if workflow_id:
        metadata.setdefault("trace_metadata", {})
        metadata["trace_metadata"]["workflow_id"] = str(workflow_id)
    return metadata


def configure_observability() -> None:
    """Wire LangFuse LiteLLM callbacks and optional OTLP exporter once per process."""

    global _observability_configured  # noqa: PLW0603
    if _observability_configured:
        return

    if settings.langfuse_enabled:
        if settings.langfuse_public_key:
            os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
        if settings.langfuse_secret_key:
            os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
        if settings.langfuse_host:
            os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host.rstrip("/"))

        litellm.success_callback = ["langfuse"]
        litellm.failure_callback = ["langfuse"]
        logger.info(
            "observability.langfuse.enabled",
            agent_id="api_lifespan",
            swarm_id="global",
            task_id="observability",
            host=settings.langfuse_host or "cloud",
        )

    if settings.opentelemetry_enabled and settings.opentelemetry_exporter_otlp_endpoint.strip():
        try:
            from opentelemetry import trace
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            resource = Resource.create(
                {
                    "service.name": settings.opentelemetry_service_name,
                    "deployment.environment": settings.log_environment,
                },
            )
            provider = TracerProvider(resource=resource)
            exporter = OTLPSpanExporter(endpoint=settings.opentelemetry_exporter_otlp_endpoint.strip())
            provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(provider)
            logger.info(
                "observability.otel.enabled",
                agent_id="api_lifespan",
                swarm_id="global",
                task_id="observability",
                endpoint=settings.opentelemetry_exporter_otlp_endpoint,
            )
        except ImportError as exc:
            logger.warning(
                "observability.otel.import_failed",
                agent_id="api_lifespan",
                swarm_id="global",
                task_id="observability",
                error=str(exc),
            )

    _observability_configured = True


__all__ = ["build_langfuse_metadata", "configure_observability"]
