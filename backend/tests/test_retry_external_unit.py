"""Unit coverage for shared async retry helper."""

from __future__ import annotations

import pytest

from app.core.retry_external import retry_async_call


@pytest.mark.asyncio
async def test_retry_async_call_when_transient_then_recovers() -> None:
    attempts = {"n": 0}

    async def _factory() -> str:
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise TimeoutError("transient")
        return "ok"

    value = await retry_async_call(
        _factory,
        max_attempts=3,
        initial_wait_sec=0.01,
        max_wait_sec=0.05,
    )
    assert value == "ok"
    assert attempts["n"] == 2


@pytest.mark.asyncio
async def test_retry_async_call_when_non_retriable_then_raises_once() -> None:
    attempts = {"n": 0}

    async def _factory() -> str:
        attempts["n"] += 1
        raise RuntimeError("hard_fail")

    with pytest.raises(RuntimeError):
        await retry_async_call(
            _factory,
            max_attempts=4,
            retry_predicate=lambda _exc: False,
        )
    assert attempts["n"] == 1
