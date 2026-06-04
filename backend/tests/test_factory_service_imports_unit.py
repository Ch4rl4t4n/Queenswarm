"""Factory services must import ORM symbols used in snapshot compose."""

from __future__ import annotations

import inspect


def test_skill_factory_service_references_agent_suggestion_import() -> None:
    from app.application.services import skill_factory_service as mod

    source = inspect.getsource(mod)
    assert "from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion" in source
    assert "AgentSuggestion" in source


def test_content_pack_factory_service_references_agent_suggestion_import() -> None:
    from app.application.services import content_pack_factory_service as mod

    source = inspect.getsource(mod)
    assert "from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion" in source
    assert "AgentSuggestion" in source
