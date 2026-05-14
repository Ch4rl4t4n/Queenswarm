"""Compatibility shim — canonical ORM: ``app.infrastructure.persistence.models.workflow``."""

from __future__ import annotations

from app.infrastructure.persistence.models.workflow import Workflow, WorkflowStep

__all__ = ["Workflow", "WorkflowStep"]
