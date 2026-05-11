"""Schemas for Auto Workflow Breaker API and LiteLLM JSON validation."""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import AgentRole


class DecomposeWorkflowRequest(BaseModel):
    """Inbound operator request defining the hive decomposition job."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    task_text: Annotated[str, Field(min_length=8, max_length=50_000)]
    matching_recipe_id: uuid.UUID | None = None
    enrich_from_chroma_recipes: bool = Field(
        default=False,
        description="When True, cosine-match the Recipe Library and inject context.",
    )


class WorkflowStepBrief(BaseModel):
    """Thin projection of persisted steps suitable for dashboards."""

    model_config = ConfigDict(extra="ignore")

    id: uuid.UUID
    step_order: int
    description: str
    agent_role: AgentRole


class DecomposeWorkflowResponse(BaseModel):
    """Confirmation payload after decomposition lands in Postgres."""

    model_config = ConfigDict(extra="ignore")

    workflow_id: uuid.UUID
    status: str
    total_steps: int
    parallel_groups: list[list[int]]
    steps: list[WorkflowStepBrief]
    decomposition_rationale: str | None = None


class BreakerStepDraft(BaseModel):
    """Single decomposition row produced by the LLM."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    order: Annotated[int, Field(ge=1, le=32)]
    description: Annotated[str, Field(min_length=8)]
    agent_role: AgentRole
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    guardrails: dict[str, Any] = Field(
        ...,
        description="Must enumerate risks/mitigations aligned with scout/eval/sim guardrails.",
    )
    evaluation_criteria: dict[str, Any] = Field(
        ...,
        description="Operator-verifiable prompts for simulation-heavy paths.",
    )

    @field_validator("description")
    @classmethod
    def meaningful_description(cls, value: str) -> str:
        """Trim whitespace and require multi-token operator guidance."""

        text = value.strip()
        if len(text.split()) < 2:
            msg = "Each step description must include at least two tokens."
            raise ValueError(msg)
        return text


class BreakerDecomposition(BaseModel):
    """Structured decomposition contract returned by LiteLLM clients."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    rationale: Annotated[str, Field(min_length=16)]
    parallelizable_groups: list[list[int]] = Field(default_factory=list)
    estimated_duration_sec: int | None = Field(default=None, ge=10, le=86_400)
    steps: Annotated[list[BreakerStepDraft], Field(min_length=3, max_length=7)]

    @model_validator(mode="after")
    def validate_unique_orders(self) -> Self:
        """Ensure LLM did not emit duplicate ordering keys."""

        orders = [step.order for step in self.steps]
        if len(orders) != len(set(orders)):
            msg = "Duplicate step order values are not allowed."
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_parallel_references(self) -> Self:
        """Guarantee parallel groups only reference real step orders."""

        valid = {step.order for step in self.steps}
        for group in self.parallelizable_groups:
            for idx in group:
                if idx not in valid:
                    msg = f"Parallel group references unknown step order {idx}."
                    raise ValueError(msg)
        return self
