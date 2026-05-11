"""Role-specialized bees for Phase D (one class per :class:`~app.models.enums.AgentRole` worker)."""

from __future__ import annotations

import uuid
from abc import abstractmethod
from typing import Any, ClassVar

from app.agents.base_agent import BaseAgent
from app.core.config import settings
from app.models.enums import AgentRole


class RoleBee(BaseAgent):
    """Shared telemetry + waggle hooks for colony specialists."""

    def waggle_cue(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Augment base waggle vector with declared role alignment."""

        base = super().waggle_cue(payload)
        base["expected_role"] = self.expected_role.value
        return base

    @abstractmethod
    async def execute(
        self,
        *,
        payload: dict[str, Any],
        task_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Execute the specialist bee contract."""

    async def _emit_standard(
        self,
        *,
        payload: dict[str, Any],
        task_id: uuid.UUID | None,
        hive_note: str,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Structured placeholder output until LangGraph subgraphs land (Phase E)."""

        out: dict[str, Any] = {
            "agent_role": self._agent.role.value,
            "expected_role": self.expected_role.value,
            "task_id": str(task_id) if task_id else None,
            "payload_keys": sorted(payload.keys()),
            "hive_phase": "D",
            "hive_note": hive_note,
        }
        if extra:
            out.update(extra)
        return out


class ScraperBee(RoleBee):
    """Scout / ingest surfaces — bounded harvest + provenance."""

    expected_role = AgentRole.SCRAPER

    async def execute(
        self,
        *,
        payload: dict[str, Any],
        task_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Stage scrape parameters for downstream verification (no live HTTP in Phase D)."""

        return await self._emit_standard(
            payload=payload,
            task_id=task_id,
            hive_note="Scraper bee: ingest queue + provenance envelope (Phase D stub).",
            extra={"guardrail": "respect robots + rate limits"},
        )


class EvaluatorBee(RoleBee):
    """Rubric + evidence alignment before user-facing truth."""

    expected_role = AgentRole.EVALUATOR

    async def execute(
        self,
        *,
        payload: dict[str, Any],
        task_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Emit evaluation scaffolding keyed off workflow evaluation_criteria."""

        return await self._emit_standard(
            payload=payload,
            task_id=task_id,
            hive_note="Evaluator bee: score claims vs rubric (Phase D stub).",
            extra={"threshold_ref": float(settings.reward_threshold_pass)},
        )


class SimulatorBee(RoleBee):
    """Docker-gated roll-forward predictions (ties into rapid loop)."""

    expected_role = AgentRole.SIMULATOR

    async def execute(
        self,
        *,
        payload: dict[str, Any],
        task_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Return synthetic verifier when dev stubs are enabled; else pending simulation."""

        if settings.simulator_stub_auto_verify:
            conf = max(float(settings.reward_threshold_pass), 0.99)
            return await self._emit_standard(
                payload=payload,
                task_id=task_id,
                hive_note="Simulator bee: synthetic PASS (simulator_stub_auto_verify).",
                extra={
                    "verification_passed": True,
                    "confidence": conf,
                },
            )

        return await self._emit_standard(
            payload=payload,
            task_id=task_id,
            hive_note="Simulator bee: awaits sandbox binding (Phase D stub).",
            extra={
                "verification_passed": False,
                "confidence": 0.0,
            },
        )


class ReporterBee(RoleBee):
    """Human-safe summaries after simulation gates."""

    expected_role = AgentRole.REPORTER

    async def execute(
        self,
        *,
        payload: dict[str, Any],
        task_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Format guarded digests for operators."""

        return await self._emit_standard(
            payload=payload,
            task_id=task_id,
            hive_note="Reporter bee: verified-only outward messaging (Phase D stub).",
        )


class TraderBee(RoleBee):
    """Risk-scoped trade narratives + signal simulation hand-offs."""

    expected_role = AgentRole.TRADER

    async def execute(
        self,
        *,
        payload: dict[str, Any],
        task_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Route financial reasoning through simulator-backed checks."""

        return await self._emit_standard(
            payload=payload,
            task_id=task_id,
            hive_note="Trader bee: scenario cards before execution (Phase D stub).",
            extra={"risk_layer": "sandbox_first"},
        )


class MarketerBee(RoleBee):
    """Campaign orchestration with compliance overlays."""

    expected_role = AgentRole.MARKETER

    async def execute(
        self,
        *,
        payload: dict[str, Any],
        task_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Package audience + channel hypotheses."""

        return await self._emit_standard(
            payload=payload,
            task_id=task_id,
            hive_note="Marketer bee: channel + compliance matrix (Phase D stub).",
        )


class BlogWriterBee(RoleBee):
    """Long-form content with citation + simulator prerequisites."""

    expected_role = AgentRole.BLOG_WRITER

    async def execute(
        self,
        *,
        payload: dict[str, Any],
        task_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Draft blog payloads after evaluator/simulator gates."""

        return await self._emit_standard(
            payload=payload,
            task_id=task_id,
            hive_note="Blog writer bee: outline → draft with citations (Phase D stub).",
        )


class SocialPosterBee(RoleBee):
    """Short-form social surfaces with brand safety."""

    expected_role = AgentRole.SOCIAL_POSTER

    async def execute(
        self,
        *,
        payload: dict[str, Any],
        task_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Construct post drafts for hive review."""

        return await self._emit_standard(
            payload=payload,
            task_id=task_id,
            hive_note="Social poster bee: char-limit + safety lint (Phase D stub).",
        )


class LearnerBee(RoleBee):
    """Imitation + pollen-aware policy tweaks."""

    expected_role = AgentRole.LEARNER

    async def execute(
        self,
        *,
        payload: dict[str, Any],
        task_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Emit learning deltas referencing neighborhood pollen."""

        return await self._emit_standard(
            payload=payload,
            task_id=task_id,
            hive_note="Learner bee: imitation hooks + neighbor pollen stats (Phase D stub).",
            extra={"pollen_snapshot": float(self.pollen_points)},
        )


class RecipeKeeperBee(RoleBee):
    """Recipe Library curation + promotion cadence."""

    expected_role = AgentRole.RECIPE_KEEPER

    async def execute(
        self,
        *,
        payload: dict[str, Any],
        task_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Coordinate catalog hygiene for verified workflows."""

        return await self._emit_standard(
            payload=payload,
            task_id=task_id,
            hive_note="Recipe keeper bee: catalog promotion + mirrors (Phase D stub).",
        )


__all__ = [
    "BlogWriterBee",
    "EvaluatorBee",
    "LearnerBee",
    "MarketerBee",
    "RecipeKeeperBee",
    "ReporterBee",
    "RoleBee",
    "ScraperBee",
    "SimulatorBee",
    "SocialPosterBee",
    "TraderBee",
]
