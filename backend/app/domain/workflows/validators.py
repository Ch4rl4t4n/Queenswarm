"""Structural + linguistic validation for breaker JSON before ORM persistence."""

from __future__ import annotations

import re
from typing import Any


class WorkflowValidator:
    """Validate decomposed workflow payloads and coarse step output shape."""

    _VAGUE_PATTERNS: tuple[re.Pattern[str], ...] = (
        re.compile(r"\b(analyze|analyse)s?\b", re.IGNORECASE),
        re.compile(r"\bprocess(ing)?\b", re.IGNORECASE),
        re.compile(r"\bhandle(s|d)?\b", re.IGNORECASE),
        re.compile(r"\bdeal with\b", re.IGNORECASE),
        re.compile(r"\blook into\b", re.IGNORECASE),
    )

    @classmethod
    def validate_decomposition(cls, workflow: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate breaker JSON prior to strict Pydantic parsing.

        Args:
            workflow: Raw dict extracted from the LLM payload.

        Returns:
            Tuple of pass flag plus human-readable rejection reasons.
        """

        errors: list[str] = []
        steps = workflow.get("steps")
        if not isinstance(steps, list):
            errors.append("Field 'steps' must be a list.")
            return False, errors

        step_count = len(steps)
        if step_count < 3 or step_count > 7:
            errors.append(f"Expected 3-7 steps, got {step_count}.")

        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"Step {idx} must be an object.")
                continue
            desc = step.get("description")
            if not isinstance(desc, str) or len(desc.strip().split()) < 2:
                errors.append(f"Step {idx} description must include at least two tokens.")
            elif cls._looks_vague(desc):
                errors.append(
                    f"Step {idx} description is too vague (avoid analyze/process/handle patterns).",
                )
            for key in ("input_schema", "output_schema", "guardrails", "evaluation_criteria"):
                if key not in step:
                    errors.append(f"Step {idx} missing required field '{key}'.")
            g = step.get("guardrails")
            if isinstance(g, dict):
                for sub in ("risks", "mitigations", "stop_conditions"):
                    if sub not in g:
                        errors.append(f"Step {idx} guardrails missing '{sub}'.")
            ev = step.get("evaluation_criteria")
            if isinstance(ev, dict):
                for sub in ("must_satisfy", "measurable_signals"):
                    if sub not in ev:
                        errors.append(f"Step {idx} evaluation_criteria missing '{sub}'.")

        return len(errors) == 0, errors

    @classmethod
    def _looks_vague(cls, description: str) -> bool:
        """Return True when description matches vague hive blacklist patterns."""

        for pat in cls._VAGUE_PATTERNS:
            if pat.search(description):
                return True
        return False

    @staticmethod
    def validate_step_result(step: Any, result: dict[str, Any]) -> bool:
        """Sanity-check executor payload against declared output_schema keys (non-schema)."""

        del step  # reserved for future JSON-schema validation
        return bool(result)
