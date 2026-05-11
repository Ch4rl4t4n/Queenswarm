"""Shared LangGraph state for decentralized sub-swarm workflow execution."""

from __future__ import annotations

from operator import add
from typing import Annotated, Any, NotRequired, TypedDict

from typing_extensions import Required


class SubSwarmWorkflowState(TypedDict, total=False):
    """In-process hive graph state keyed by swarm + workflow lineage."""

    swarm_id: Required[str]
    workflow_id: Required[str]
    task_uuid: NotRequired[str | None]
    payload: Required[dict[str, Any]]
    traces: Annotated[list[str], add]
    step_outputs: Annotated[list[dict[str, Any]], add]
    step_manifest: Required[list[dict[str, Any]]]
    error: NotRequired[str | None]
    error_detail: NotRequired[str | None]
    global_sync_recommended: Required[bool]


__all__ = ["SubSwarmWorkflowState"]
