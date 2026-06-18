"""Unit tests for Mission Home Skill Factory harness strip (POS-V)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.mission_skill_factory_harness_service import (
    compose_mission_skill_factory_harness_strip,
)


@pytest.mark.asyncio
async def test_compose_harness_strip_when_llm_blocked() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()

    with patch("app.application.services.mission_skill_factory_harness_service.settings") as mock_settings:
        mock_settings.skill_factory_enabled = True
        with patch(
            "app.application.services.mission_skill_factory_harness_service.personal_os_skill_factory_commercial_enabled",
            return_value=False,
        ):
            with patch(
                "app.application.services.mission_skill_factory_harness_service.resolve_factory_llm_readiness",
                AsyncMock(
                    return_value=type(
                        "Llm",
                        (),
                        {"build_allowed": False, "smoke_ok": None},
                    )(),
                ),
            ):
                with patch(
                    "app.application.services.mission_skill_factory_harness_service.count_skill_opportunity_statuses",
                    AsyncMock(
                        return_value=type(
                            "Counts",
                            (),
                            {"actionable": 0, "building": 0, "failed": 0},
                        )(),
                    ),
                ):
                    with patch(
                        "app.application.services.mission_skill_factory_harness_service.list_tenant_skills",
                        AsyncMock(return_value=[]),
                    ):
                        with patch(
                            "app.application.services.mission_skill_factory_harness_service._forge_quality_by_skill_id",
                            AsyncMock(return_value={}),
                        ):
                            strip = await compose_mission_skill_factory_harness_strip(
                                session,
                                tenant_id=tenant_id,
                                first_run_complete=True,
                            )

    assert strip.enabled is True
    assert strip.llm_ready is False
    assert strip.personal_os_lite is True
    assert strip.queue_href.endswith("#queue")


@pytest.mark.asyncio
async def test_compose_harness_strip_when_verified_in_library() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    skill_row = type("Skill", (), {"id": uuid.uuid4(), "slug": "my-skill"})()

    with patch("app.application.services.mission_skill_factory_harness_service.settings") as mock_settings:
        mock_settings.skill_factory_enabled = True
        with patch(
            "app.application.services.mission_skill_factory_harness_service.personal_os_skill_factory_commercial_enabled",
            return_value=False,
        ):
            with patch(
                "app.application.services.mission_skill_factory_harness_service.resolve_factory_llm_readiness",
                AsyncMock(
                    return_value=type(
                        "Llm",
                        (),
                        {"build_allowed": True, "smoke_ok": True},
                    )(),
                ),
            ):
                with patch(
                    "app.application.services.mission_skill_factory_harness_service.count_skill_opportunity_statuses",
                    AsyncMock(
                        return_value=type(
                            "Counts",
                            (),
                            {"actionable": 0, "building": 0, "failed": 0},
                        )(),
                    ),
                ):
                    with patch(
                        "app.application.services.mission_skill_factory_harness_service.list_tenant_skills",
                        AsyncMock(return_value=[skill_row]),
                    ):
                        with patch(
                            "app.application.services.mission_skill_factory_harness_service._forge_quality_by_skill_id",
                            AsyncMock(return_value={}),
                        ):
                            with patch(
                                "app.application.services.mission_skill_factory_harness_service.assess_tenant_skill_sellable",
                                return_value=type(
                                    "Assessment",
                                    (),
                                    {"tier": "sellable"},
                                )(),
                            ):
                                strip = await compose_mission_skill_factory_harness_strip(
                                    session,
                                    tenant_id=tenant_id,
                                    first_run_complete=True,
                                )

    assert strip.enabled is True
    assert strip.verified_count == 1
    assert strip.library_href.endswith("#library")
