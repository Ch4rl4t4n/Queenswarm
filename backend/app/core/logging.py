"""Structured JSON logging using structlog and contextvars for bee-hive tracing."""

from __future__ import annotations

import logging
from typing import Any

import structlog
from structlog.typing import FilteringBoundLogger


def _append_static_log_context(
    logger: Any, method_name: str, event_dict: dict[str, Any]  # noqa: ANN401
) -> dict[str, Any]:
    """Attach static service metadata for centralized log aggregation."""

    del logger, method_name
    event_dict.setdefault("service", _STATIC_LOG_CONTEXT["service"])
    event_dict.setdefault("environment", _STATIC_LOG_CONTEXT["environment"])
    event_dict.setdefault("instance_id", _STATIC_LOG_CONTEXT["instance_id"])
    return event_dict


_STATIC_LOG_CONTEXT = {
    "service": "queenswarm-api",
    "environment": "development",
    "instance_id": "unknown",
}


def configure_logging(
    level: str = "INFO",
    *,
    service_name: str = "queenswarm-api",
    environment: str = "development",
    instance_id: str = "unknown",
) -> None:
    """Configure structlog for JSON logs with swarm task context merge support.

    Processors emit ISO timestamps, severity, logger name bound via `get_logger`,
    arbitrary context fields (`agent_id`, `swarm_id`, `task_id`, etc.), and the
    canonical ``event`` key for the log message.

    Args:
        level: Minimum log level name (default INFO).
    """

    log_level_name = level.upper()
    log_level_value = getattr(logging, log_level_name, logging.INFO)
    _STATIC_LOG_CONTEXT["service"] = str(service_name).strip() or "queenswarm-api"
    _STATIC_LOG_CONTEXT["environment"] = str(environment).strip() or "development"
    _STATIC_LOG_CONTEXT["instance_id"] = str(instance_id).strip() or "unknown"

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _append_static_log_context,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level_value),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> FilteringBoundLogger:
    """Return a structlog logger with the module ``name`` and JSON ``logger`` field.

    Bee-hive context fields (``agent_id``, ``swarm_id``, ``task_id``, ``workflow_id``,
    ``recipe_id``, ``pollen_earned``) are applied via ``structlog.contextvars.bind_contextvars``
    elsewhere in the application so each log line carries swarm correlation data.

    Args:
        name: Logger namespace, conventionally ``__name__`` of the calling module.

    Returns:
        Configured FilteringBoundLogger instance.
    """

    bound = structlog.get_logger(name).bind(logger=name)
    return bound  # type: ignore[no-any-return]
