"""Aggregate host, dependency, and integration telemetry for admin command center."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from app.core.celery_health import inspect_celery_workers
from app.core.config import settings
from app.core.llm_router import llm_concurrency_snapshot
from app.core.llm_router import _openai_key_looks_configured
from app.core.readiness import collect_readiness_uncached
from app.application.services.llm_runtime_credentials import (
    get_cached_llm_key,
    provider_effective_anthropic,
    provider_effective_deepgram,
    provider_effective_elevenlabs,
    provider_effective_grok,
    provider_effective_openai,
)
from app.application.services.command_center_telemetry import read_host_history, record_host_sample
from app.application.services.monitoring_snapshot import _docker_running_sync, _host_metrics_sync
from app.core.redis_client import read_minute_counter_sum
from app.presentation.api.routers.system_status import _hive_gauges, _host_pressure, _simulation_task_counts


def _gb(bytes_value: int) -> float:
    """Convert bytes to gigabytes rounded."""

    return round(float(bytes_value) / (1024**3), 2)


def _llm_source(provider: str) -> str:
    """Return env/vault/none for one LLM provider."""

    if get_cached_llm_key(provider):
        return "vault"
    env_map = {
        "grok": bool((settings.grok_api_key or "").strip()),
        "anthropic": bool((settings.anthropic_api_key or "").strip()),
        "openai": bool((settings.openai_api_key or "").strip()),
        "deepgram": bool((settings.deepgram_api_key or "").strip()),
        "elevenlabs": bool((settings.elevenlabs_api_key or "").strip()),
    }
    return "env" if env_map.get(provider) else "none"


def _dependency_rows(readiness: dict[str, Any], celery_snapshot: dict[str, int | bool | str]) -> list[dict[str, Any]]:
    """Flatten readiness checks into UI rows."""

    checks = readiness.get("checks") or {}
    rows: list[dict[str, Any]] = []
    mapping = [
        ("postgres", "PostgreSQL", "data"),
        ("redis", "Redis", "data"),
        ("neo4j", "Neo4j graph", "data"),
        ("chroma", "Vector store (Chroma/pgvector)", "data"),
    ]
    for key, label, category in mapping:
        layer = checks.get(key) or {}
        rows.append(
            {
                "key": key,
                "label": label,
                "category": category,
                "ok": bool(layer.get("ok")),
                "latency_ms": layer.get("latency_ms"),
                "error": layer.get("error"),
            },
        )
    rows.append(
        {
            "key": "celery",
            "label": "Celery workers",
            "category": "queue",
            "ok": bool(celery_snapshot.get("ok")),
            "latency_ms": None,
            "error": None if celery_snapshot.get("ok") else "no_workers",
            "detail": f"{celery_snapshot.get('workers_up', 0)} workers · active {celery_snapshot.get('active_tasks', 0)}",
        },
    )
    return rows


def _llm_provider_rows() -> list[dict[str, Any]]:
    """List LiteLLM-routed providers used across the hive."""

    specs = [
        ("grok", "Grok / xAI", "Primary LLM route", "xai/"),
        ("anthropic", "Claude", "Fallback LLM route", "anthropic/"),
        ("openai", "OpenAI", "Cheap / utility route", "openai/"),
        ("deepgram", "Deepgram", "Ballroom STT", "stt"),
        ("elevenlabs", "ElevenLabs", "Ballroom TTS", "tts"),
    ]
    effective = {
        "grok": provider_effective_grok(),
        "anthropic": provider_effective_anthropic(),
        "openai": provider_effective_openai(),
        "deepgram": provider_effective_deepgram(),
        "elevenlabs": provider_effective_elevenlabs(),
    }
    rows: list[dict[str, Any]] = []
    for key, label, role, route in specs:
        raw = effective.get(key, "")
        configured = bool(raw) if key != "openai" else _openai_key_looks_configured(raw)
        rows.append(
            {
                "provider": key,
                "label": label,
                "role": role,
                "route": route,
                "configured": configured,
                "source": _llm_source(key) if configured else "none",
            },
        )
    return rows


def _integration_rows() -> list[dict[str, Any]]:
    """Voice + observability integration readiness."""

    return [
        {
            "key": "billing_checkout",
            "label": "Billing checkout",
            "category": "billing",
            "ok": True,
            "detail": "In-app checkout removed.",
            "source": "removed",
        },
        {
            "key": "voice_enabled",
            "label": "Voice module",
            "category": "ballroom",
            "ok": bool(settings.voice_enabled),
            "detail": "VOICE_ENABLED flag",
            "source": "env",
        },
        {
            "key": "opentelemetry",
            "label": "OpenTelemetry",
            "category": "observability",
            "ok": bool(settings.opentelemetry_enabled and (settings.opentelemetry_exporter_otlp_endpoint or "").strip()),
            "detail": settings.opentelemetry_exporter_otlp_endpoint or "not configured",
            "source": "env",
        },
    ]


def _docker_snapshot() -> dict[str, Any]:
    """Return Docker visibility for compose stack."""

    running_count, unavailable = _docker_running_sync()
    if unavailable:
        return {
            "available": False,
            "running_total": None,
            "queenswarm_running": None,
            "containers": [],
        }
    try:
        import docker

        client = docker.from_env()
        running = client.containers.list(filters={"status": "running"})
        queenswarm = [c for c in running if "queenswarm" in (c.name or "").lower()]
        containers: list[dict[str, str]] = []
        for container in queenswarm[:16]:
            tags = container.image.tags if container.image else []
            containers.append(
                {
                    "name": str(container.name or ""),
                    "image": str(tags[0] if tags else "unknown"),
                    "status": str(container.status or "running"),
                },
            )
        return {
            "available": True,
            "running_total": len(running),
            "queenswarm_running": len(queenswarm),
            "containers": containers,
        }
    except Exception:  # noqa: BLE001
        return {
            "available": False,
            "running_total": running_count,
            "queenswarm_running": None,
            "containers": [],
        }


async def build_command_center_snapshot() -> dict[str, Any]:
    """Compose admin command center payload from existing probes."""

    readiness, _ = await collect_readiness_uncached()
    host_raw, host_pressure, celery_snapshot, docker_info = await asyncio.gather(
        asyncio.to_thread(_host_metrics_sync),
        asyncio.to_thread(_host_pressure),
        asyncio.to_thread(inspect_celery_workers),
        asyncio.to_thread(_docker_snapshot),
    )
    cpu_pct, mem_pct, disk_pct, pressure, pressure_reason = host_pressure
    limiter = llm_concurrency_snapshot()

    await record_host_sample(cpu_percent=cpu_pct, memory_percent=mem_pct, disk_percent=disk_pct)
    host_history = await read_host_history(limit=96)
    rate_limit_blocks_5m = await read_minute_counter_sum("rate_limit_blocks", last_minutes=5)
    scaling_events_5m = await read_minute_counter_sum("scaling_events", last_minutes=5)

    agents_total = agents_running = tasks_running = tasks_pending = 0
    sim_running = sim_pending = 0
    db_ok = bool((readiness.get("checks") or {}).get("postgres", {}).get("ok"))
    if db_ok:
        try:
            agents_total, agents_running, tasks_running, tasks_pending = await _hive_gauges()
            sim_running, sim_pending = await _simulation_task_counts()
        except Exception:  # noqa: BLE001
            pass

    llm_rows = _llm_provider_rows()
    return {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "instance_id": settings.instance_id,
        "host": {
            "cpu_percent": cpu_pct,
            "memory_percent": mem_pct,
            "disk_percent": disk_pct,
            "memory_used_gb": _gb(int(host_raw.get("memory_used_bytes") or 0)),
            "memory_total_gb": _gb(int(host_raw.get("memory_total_bytes") or 0)),
            "disk_used_gb": _gb(int(host_raw.get("disk_used_bytes") or 0)),
            "disk_total_gb": _gb(int(host_raw.get("disk_total_bytes") or 0)),
            "swap_percent": float(host_raw.get("swap_percent") or 0.0),
            "resource_pressure": pressure,
            "resource_pressure_reason": pressure_reason,
        },
        "dependencies": _dependency_rows(readiness, celery_snapshot),
        "llm_providers": llm_rows,
        "integrations": _integration_rows(),
        "docker": docker_info,
        "host_history": host_history,
        "telemetry": {
            "rate_limit_blocks_5m": rate_limit_blocks_5m,
            "scaling_events_5m": scaling_events_5m,
        },
        "hive_load": {
            "agents_total": agents_total,
            "agents_running": agents_running,
            "tasks_running": tasks_running,
            "tasks_pending": tasks_pending,
            "simulation_tasks_running": sim_running,
            "simulation_tasks_pending": sim_pending,
            "llm_in_flight": int(limiter["llm_in_flight"]),
            "llm_concurrency_limit": int(limiter["llm_limit"]),
            "simulation_in_flight": int(limiter["simulation_in_flight"]),
            "simulation_concurrency_limit": int(limiter["simulation_limit"]),
            "simulations_enabled": bool(settings.simulations_enabled),
        },
        "summary": {
            "dependencies_ok": all(row["ok"] for row in _dependency_rows(readiness, celery_snapshot)),
            "llm_routes_ok": any(row["configured"] for row in llm_rows if row["provider"] in {"grok", "anthropic", "openai"}),
            "integrations_ok": True,
        },
    }


__all__ = ["build_command_center_snapshot"]
