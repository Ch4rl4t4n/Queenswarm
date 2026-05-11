"""String-backed enumerations mirrored in PostgreSQL for hive orchestration."""

from __future__ import annotations

from enum import Enum


class AgentRole(str, Enum):
    """Specialization of bee workers routed by the LangGraph supervisor."""

    SCRAPER = "scraper"
    EVALUATOR = "evaluator"
    SIMULATOR = "simulator"
    REPORTER = "reporter"
    TRADER = "trader"
    MARKETER = "marketer"
    BLOG_WRITER = "blog_writer"
    SOCIAL_POSTER = "social_poster"
    LEARNER = "learner"
    RECIPE_KEEPER = "recipe_keeper"


class AgentStatus(str, Enum):
    """Runtime health of autonomous agents."""

    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    OFFLINE = "offline"


class SwarmPurpose(str, Enum):
    """Decentralized colony purpose for local hive minds."""

    SCOUT = "scout"
    EVAL = "eval"
    SIMULATION = "simulation"
    ACTION = "action"


class TaskStatus(str, Enum):
    """Lifecycle of atomic execution units surfaced to operators."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """High-level swarm routing signal for backlog ordering."""

    SCRAPE = "scrape"
    EVALUATE = "evaluate"
    SIMULATE = "simulate"
    REPORT = "report"
    TRADE_ANALYSIS = "trade_analysis"
    SOCIAL_POST = "social_post"
    BLOG_POST = "blog_post"


class WorkflowStatus(str, Enum):
    """Automated decomposition + execution telemetry for breaker output."""

    PENDING = "pending"
    DECOMPOSING = "decomposing"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(str, Enum):
    """Step-level guardrail execution checkpoints."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SimulationResult(str, Enum):
    """Sandbox outcome before user-visible surfaces."""

    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"


class BudgetPeriod(str, Enum):
    """Cost governor accrual window."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class HiveAsyncRunLifecycle(str, Enum):
    """Postgres audit states for deferred LangGraph runs."""

    QUEUED = "queued"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


__all__ = [
    "AgentRole",
    "AgentStatus",
    "BudgetPeriod",
    "HiveAsyncRunLifecycle",
    "SimulationResult",
    "StepStatus",
    "SwarmPurpose",
    "TaskStatus",
    "TaskType",
    "WorkflowStatus",
]
