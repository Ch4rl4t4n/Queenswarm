"""API unit tests for NP2 publish creative rubric route."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_user_with_tenant_role


@pytest.fixture
def restore_overrides() -> None:
    yield
    app.dependency_overrides.clear()


def _owner_principal() -> dict[str, object]:
    return {
        "user": type("U", (), {"id": uuid.uuid4()})(),
        "tenant_id": uuid.uuid4(),
        "tenant_role": "owner",
        "permissions": ["*"],
    }


@pytest.mark.asyncio
async def test_social_publish_creative_rubric_post(restore_overrides: None) -> None:
    from app.application.services.publish_creative_rubric_service import PublishCreativeRubricOut

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    deliverable_id = uuid.uuid4()
    rubric = PublishCreativeRubricOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        template_id="marketing-creative",
        template_name="Marketing Creative (Riverflow)",
        overall_score=0.81,
        pass_threshold=0.75,
        passed=True,
        operator_hint="Creative rubric pass",
    )

    with (
        patch(
            "app.presentation.api.routers.social_publish.fetch_owned_deliverable",
            AsyncMock(return_value=MagicMock(structured_json={"body": "Launch copy with CTA."})),
        ),
        patch(
            "app.presentation.api.routers.social_publish.evaluate_publish_pack_creative_rubric",
            AsyncMock(return_value=rubric),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/social-publish/{deliverable_id}/creative-rubric",
                headers={"Authorization": "Bearer x"},
            )

    assert response.status_code == 200
    assert response.json()["overall_score"] == 0.81
