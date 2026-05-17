"""Shared async retry surface for LiteLLM and outbound connector HTTP."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from tenacity import (
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)
from tenacity.asyncio import AsyncRetrying

from app.core.config import get_settings
from app.core.logging import get_logger

T = TypeVar("T")
logger = get_logger(__name__)


def _default_retry_predicate(exc: BaseException) -> bool:
    """Return True for common transient transport / capacity failures."""

    name = type(exc).__name__
    if "Timeout" in name or "ReadTimeout" in name:
        return True
    if "Connection" in name or "Transport" in name or "IncompleteRead" in name:
        return True
    if "OperationalError" in name or "DisconnectionError" in name or "InterfaceError" in name:
        return True
    lowered = str(exc).lower()
    transient_markers = (
        "rate limit",
        "429",
        "503",
        "502",
        "temporarily unavailable",
        "overloaded",
        "timeout",
        "connection reset",
        "could not connect",
        "too many connections",
    )
    return any(marker in lowered for marker in transient_markers)


async def retry_async_call(
    factory: Callable[[], Awaitable[T]],
    *,
    max_attempts: int | None = None,
    initial_wait_sec: float | None = None,
    max_wait_sec: float | None = None,
    retry_predicate: Callable[[BaseException], bool] | None = None,
) -> T:
    """Run ``factory`` until success or retries exhaust.

    Args:
        factory: Coroutine-producing callable evaluated on every attempt.
        max_attempts: Override attempt budget (defaults hive settings composite).
        initial_wait_sec: First backoff slice (defaults settings).
        max_wait_sec: Exponential jitter ceiling (defaults settings).
        retry_predicate: Predicate returning True when exception is retriable.

    Returns:
        Successful coroutine output.

    Raises:
        Last exception when retries exhaust or predicate rejects.
    """

    settings = get_settings()
    attempts = int(max_attempts or settings.llm_retry_max_attempts)
    initial = float(initial_wait_sec or settings.llm_retry_initial_wait_sec)
    ceiling = float(max_wait_sec or settings.llm_retry_max_wait_sec)
    predicate = retry_predicate or _default_retry_predicate

    attempt_no = 0
    result: Any = None
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(max(attempts, 1)),
        wait=wait_exponential_jitter(initial=initial, max=ceiling),
        retry=retry_if_exception(predicate),
        reraise=True,
    ):
        with attempt:
            attempt_no += 1
            if attempt_no > 1:
                logger.warning(
                    "retry_external.retrying",
                    agent_id="retry_external",
                    swarm_id="infra",
                    task_id="transient_retry",
                    attempt=attempt_no,
                    max_attempts=attempts,
                )
            result = await factory()
    return result  # type: ignore[no-any-return]


__all__ = ["retry_async_call"]
