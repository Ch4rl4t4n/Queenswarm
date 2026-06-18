"""Unit tests for Mission Home Skill Factory harness strip (POS-V)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.mission_skill_factory_harness_service import (
    compose_mission_skill_factory_harness_strip,
)

_MOCK_EXPORT_CHANNELS = type(
    "ExportChannels",
    (),
    {
        "manual_export_ready": True,
        "github_pr_ready": False,
        "gumroad_draft_ready": False,
        "gumroad_publish_ready": False,
        "gumroad_setup_hint": "Manual upload: exports/gumroad-upload/*.tar.gz",
        "github_setup_hint": "",
    },
)()


def _patch_export_channels():
    return patch(
        "app.application.services.mission_skill_factory_harness_service.resolve_factory_export_readiness",
        AsyncMock(return_value=_MOCK_EXPORT_CHANNELS),
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
                            with _patch_export_channels():
                                session.get = AsyncMock(
                                    return_value=type("Tenant", (), {"operator_settings": {}})(),
                                )
                                strip = await compose_mission_skill_factory_harness_strip(
                                    session,
                                    tenant_id=tenant_id,
                                    first_run_complete=True,
                                )

    assert strip.enabled is True
    assert strip.llm_ready is False
    assert strip.personal_os_lite is True
    assert strip.manual_export_ready is True
    assert strip.export_channels_href.endswith("#export-channels")
    assert strip.queue_href.endswith("#queue")


@pytest.mark.asyncio
async def test_compose_harness_strip_when_verified_in_library() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    skill_row = type("Skill", (), {"id": uuid.uuid4(), "slug": "my-skill", "title": "My Skill"})()

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
                            session.get = AsyncMock(
                                return_value=type("Tenant", (), {"operator_settings": {}})(),
                            )
                            with patch(
                                "app.application.services.mission_skill_factory_harness_service.assess_tenant_skill_sellable",
                                return_value=type(
                                    "Assessment",
                                    (),
                                    {
                                        "tier": "sellable",
                                        "score": 0.85,
                                        "issues": [],
                                        "recommended_for_launch": True,
                                    },
                                )(),
                            ):
                                with _patch_export_channels():
                                    strip = await compose_mission_skill_factory_harness_strip(
                                        session,
                                        tenant_id=tenant_id,
                                        first_run_complete=True,
                                    )

    assert strip.enabled is True
    assert strip.verified_count == 1
    assert strip.export_ready is True
    assert strip.export_batch_href.endswith("#export-batch")
    assert strip.library_href.endswith("#skill-factory-library")


@pytest.mark.asyncio
async def test_compose_harness_strip_counts_rebuild_eligible() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    skill_row = type("Skill", (), {"id": uuid.uuid4(), "slug": "draft-skill", "title": "Draft Skill"})()

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
                            session.get = AsyncMock(
                                return_value=type("Tenant", (), {"operator_settings": {}})(),
                            )
                            with patch(
                                    "app.application.services.mission_skill_factory_harness_service.assess_tenant_skill_sellable",
                                    return_value=type(
                                        "Assessment",
                                        (),
                                        {"tier": "draft", "score": 0.7, "issues": [], "recommended_for_launch": False},
                                    )(),
                                ):
                                    with patch(
                                        "app.application.services.mission_skill_factory_harness_service.resolve_skill_disposition",
                                        return_value=type(
                                            "Disposition",
                                            (),
                                            {"disposition": None, "attempt_count": 1},
                                        )(),
                                    ):
                                        with patch(
                                            "app.application.services.mission_skill_factory_harness_service.compute_library_sieve_verdict",
                                            return_value=type(
                                                "Sieve",
                                                (),
                                                {"verdict": "worth_retry"},
                                            )(),
                                        ):
                                            with _patch_export_channels():
                                                strip = await compose_mission_skill_factory_harness_strip(
                                                    session,
                                                    tenant_id=tenant_id,
                                                    first_run_complete=True,
                                                )

    assert strip.rebuild_eligible_count == 1
    assert strip.near_miss_count == 1
    assert "Smart rebuild" in strip.message or "near-miss" in strip.message
