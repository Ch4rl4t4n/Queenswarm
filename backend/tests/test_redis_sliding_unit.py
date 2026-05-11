"""Redis sliding-window budget validation (offline, no live Redis broker)."""

from __future__ import annotations

import pytest

from app.core.redis_client import sliding_window_reserve


@pytest.mark.asyncio
async def test_sliding_window_reserve_requires_positive_limit() -> None:
    with pytest.raises(ValueError, match="limit"):
        await sliding_window_reserve("queenswarm:test:rl", limit=0, window_sec=1.0)


@pytest.mark.asyncio
async def test_sliding_window_reserve_requires_positive_window() -> None:
    with pytest.raises(ValueError, match="window_sec"):
        await sliding_window_reserve("queenswarm:test:rl", limit=10, window_sec=0.0)
