"""Unit tests for Hive Innovation Lab."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.hive_innovation_lab import (
    InnovationBrainstormRequest,
    _infer_feature_modules,
    brainstorm_innovation_proposal,
)


def test_infer_feature_modules_hotline() -> None:
    mods = _infer_feature_modules("Add bee hotline to cockpit telegram")
    assert "bee_hotline" in mods
    assert "zero_ui_mode" in mods


@pytest.mark.asyncio
async def test_brainstorm_creates_proposal() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    with patch("app.application.services.hive_innovation_lab.settings") as mock_settings:
        mock_settings.hive_innovation_lab_enabled = True
        out = await brainstorm_innovation_proposal(
            session,
            tenant_id=uuid.uuid4(),
            body=InnovationBrainstormRequest(
                prompt="Add Hive Oracle warnings to cockpit with trust autopilot",
                category="feature",
            ),
        )
    assert out.title.startswith("Innovation:")
    assert "hive_oracle" in out.feature_modules
    session.add.assert_called_once()
