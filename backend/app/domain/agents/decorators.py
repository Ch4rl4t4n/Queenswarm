"""Execution decorators shared by autonomous bees."""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar

from app.core.config import settings

P = ParamSpec("P")
R = TypeVar("R")


def with_rapid_loop(
    func: Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[R]]:
    """Bound coroutine wrapper enforcing the rapid learning loop SLI.

    Every wrapped async method must complete within ``rapid_loop_timeout_sec`` or
    ``asyncio.TimeoutError`` propagates to LangGraph supervisors.
    """

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        timeout = float(settings.rapid_loop_timeout_sec)
        return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)

    return wrapper
