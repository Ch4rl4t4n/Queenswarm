"""Tests for factory session type detection."""

from __future__ import annotations

from types import SimpleNamespace

from app.application.services.content_pack_factory_forge import is_content_pack_factory_session
from app.application.services.skill_factory_forge import is_skill_factory_session


def test_content_pack_session_not_skill_factory() -> None:
    session = SimpleNamespace(
        goal="=== MISSION ===\nSkill Factory mention in prefix",
        context_summary={
            "raw_goal": "Content Pack Factory — produce a Gumroad-ready social content pack",
            "content_pack_factory": True,
        },
    )
    assert is_content_pack_factory_session(session) is True
    assert is_skill_factory_session(session) is False


def test_skill_factory_session() -> None:
    session = SimpleNamespace(
        goal="Skill Factory — produce agent skill",
        context_summary={"raw_goal": "Skill Factory — produce agent skill", "skill_factory": True},
    )
    assert is_skill_factory_session(session) is True
    assert is_content_pack_factory_session(session) is False
