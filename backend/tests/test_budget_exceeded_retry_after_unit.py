"""Unit tests for budget-exceeded HTTP mapping in operator/swarms routers."""

from __future__ import annotations

from app.presentation.api.routers.operator import _operator_execution_http_exception
from app.presentation.api.routers.swarms import _workflow_execution_http_exception


def test_operator_execution_http_exception_when_budget_exceeded_includes_retry_after() -> None:
    """Operator path should include Retry-After for budget throttling responses."""

    exc = _operator_execution_http_exception(
        code="budget_exceeded",
        detail="Budget cap reached.",
        traces=["step-3"],
    )
    assert exc.status_code == 429
    assert exc.headers is not None
    assert exc.headers.get("Retry-After") is not None
    assert exc.detail["code"] == "budget_exceeded"


def test_swarms_execution_http_exception_when_budget_exceeded_includes_retry_after() -> None:
    """Sub-swarm path should include Retry-After for budget throttling responses."""

    exc = _workflow_execution_http_exception(
        code="budget_exceeded",
        detail="Budget cap reached.",
        traces=["step-3"],
    )
    assert exc.status_code == 429
    assert exc.headers is not None
    assert exc.headers.get("Retry-After") is not None
    assert exc.detail["code"] == "budget_exceeded"


def test_execution_http_exception_when_non_budget_omits_retry_after() -> None:
    """Non-throttle failures should not emit Retry-After headers."""

    operator_exc = _operator_execution_http_exception(
        code="routing_failed",
        detail="No route.",
        traces=[],
    )
    swarms_exc = _workflow_execution_http_exception(
        code="routing_failed",
        detail="No route.",
        traces=[],
    )
    assert operator_exc.status_code == 422
    assert swarms_exc.status_code == 422
    assert operator_exc.headers is None
    assert swarms_exc.headers is None
