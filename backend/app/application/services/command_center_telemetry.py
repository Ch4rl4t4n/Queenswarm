"""Redis-backed host metric history for command center sparklines."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.core.redis_client import _with_redis_client

_HISTORY_KEY = "queenswarm:command_center:host_samples"
_MAX_SAMPLES = 288  # ~24h at one sample/minute
_GUARD_PREFIX = "queenswarm:command_center:sample_guard:"


async def record_host_sample(*, cpu_percent: float, memory_percent: float, disk_percent: float) -> None:
    """Append one host sample per UTC minute (deduped)."""

    now = datetime.now(tz=UTC)
    guard_key = f"{_GUARD_PREFIX}{now.strftime('%Y%m%d%H%M')}"

    async def _op(client) -> None:  # noqa: ANN001
        inserted = await client.set(guard_key, "1", nx=True, ex=120)
        if not inserted:
            return
        payload = json.dumps(
            {
                "ts": now.isoformat(),
                "cpu": round(float(cpu_percent), 2),
                "memory": round(float(memory_percent), 2),
                "disk": round(float(disk_percent), 2),
            },
        )
        await client.rpush(_HISTORY_KEY, payload)
        await client.ltrim(_HISTORY_KEY, -_MAX_SAMPLES, -1)
        await client.expire(_HISTORY_KEY, 172_800)

    try:
        await _with_redis_client(_op)
    except Exception:  # noqa: BLE001 — history is best-effort
        return


async def read_host_history(*, limit: int = 96) -> list[dict[str, Any]]:
    """Return recent host samples oldest-first."""

    capped = max(1, min(int(limit), _MAX_SAMPLES))

    async def _op(client) -> list[str]:  # noqa: ANN001
        raw = await client.lrange(_HISTORY_KEY, -capped, -1)
        return [str(item) for item in raw]

    try:
        raw_items = await _with_redis_client(_op)
    except Exception:  # noqa: BLE001
        return []

    out: list[dict[str, Any]] = []
    for item in raw_items:
        try:
            parsed = json.loads(item)
            if isinstance(parsed, dict):
                out.append(parsed)
        except json.JSONDecodeError:
            continue
    return out


__all__ = ["read_host_history", "record_host_sample"]
