"""Rate-limit guard for operator-confirmed Execution Studio live steps."""

from __future__ import annotations

import uuid

from app.core.logging import get_logger
from app.core.redis_client import sliding_window_reserve

logger = get_logger(__name__)

_CONFIRM_WINDOW_SEC = 2.0
_CONFIRM_LIMIT = 1


class ExecutionStudioConfirmThrottledError(Exception):
    """Raised when operator confirms live steps too rapidly."""

    def __init__(self, *, lane: str, retry_after_sec: float = _CONFIRM_WINDOW_SEC) -> None:
        self.lane = lane
        self.retry_after_sec = retry_after_sec
        super().__init__(f"Operator confirm throttled for lane {lane}")


async def assert_operator_confirm_allowed(
    *,
    tenant_id: uuid.UUID | None,
    lane: str,
) -> None:
    """Reject duplicate live confirms within a short sliding window."""

    if tenant_id is None:
        return

    bucket = f"execution_studio:confirm:{tenant_id}:{lane.strip().lower()}"
    allowed = await sliding_window_reserve(bucket, limit=_CONFIRM_LIMIT, window_sec=_CONFIRM_WINDOW_SEC)
    if allowed:
        return

    logger.info(
        "execution_studio.confirm_throttled",
        agent_id="reporter_bee",
        swarm_id=str(tenant_id),
        task_id=lane,
    )
    raise ExecutionStudioConfirmThrottledError(lane=lane)


__all__ = [
    "ExecutionStudioConfirmThrottledError",
    "assert_operator_confirm_allowed",
]
