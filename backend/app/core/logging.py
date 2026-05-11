"""Structured JSON logging using structlog and contextvars for bee-hive tracing."""

from __future__ import annotations

import logging

import structlog
from structlog.typing import FilteringBoundLogger


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog for JSON logs with swarm task context merge support.

    Processors emit ISO timestamps, severity, logger name bound via `get_logger`,
    arbitrary context fields (`agent_id`, `swarm_id`, `task_id`, etc.), and the
    canonical ``event`` key for the log message.

    Args:
        level: Minimum log level name (default INFO).
    """

    log_level_name = level.upper()
    log_level_value = getattr(logging, log_level_name, logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
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
