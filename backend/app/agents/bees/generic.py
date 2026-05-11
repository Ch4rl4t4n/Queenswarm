"""Default bee implementation spanning every :class:`~app.models.enums.AgentRole`."""

from __future__ import annotations

import uuid
from typing import Any

from app.agents.base_agent import BaseAgent
from app.core.config import settings
from app.models.enums import AgentRole


class GenericBee(BaseAgent):
    """Safe placeholder specialization until Phase E wires LangGraph subgraphs."""

    async def execute(
        self,
        *,
        payload: dict[str, Any],
        task_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Echo schema metadata so supervisors validate routing without vendor I/O."""

        if self._agent.role is AgentRole.SIMULATOR and settings.simulator_stub_auto_verify:
            conf = max(float(settings.reward_threshold_pass), 0.99)
            return {
                "agent_role": self._agent.role.value,
                "task_id": str(task_id) if task_id else None,
                "payload_keys": sorted(payload.keys()),
                "verification_passed": True,
                "confidence": conf,
                "hive_note": "Synthetic simulator verification (simulator_stub_auto_verify).",
            }

        payload_out: dict[str, Any] = {
            "agent_role": self._agent.role.value,
            "task_id": str(task_id) if task_id else None,
            "payload_keys": sorted(payload.keys()),
            "hive_note": "Generic bee placeholder awaiting specialized instrumented worker.",
        }
        if self._agent.role is AgentRole.SIMULATOR:
            payload_out["verification_passed"] = False
            payload_out["confidence"] = 0.0
        return payload_out
