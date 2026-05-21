"""Unit tests for skill lazy reference fetch (Phase 6 P2)."""

from __future__ import annotations

import pytest

from app.application.services.supervisor.skill_reference_fetch import fetch_skill_reference
from app.application.services.supervisor.skills import SkillLibrary


def test_skill_library_load_when_reference_mode_then_parses_references(tmp_path) -> None:
    (tmp_path / "lazy-skill.md").write_text(
        "---\nreference_mode: true\nreferences: docs/guide.md, https://example.com/doc\n---\n# Lazy\nbody",
        encoding="utf-8",
    )
    lib = SkillLibrary(skills_dir=tmp_path)
    skill = lib.load("lazy-skill")
    assert skill is not None
    assert skill.reference_mode is True
    assert skill.references == ["docs/guide.md", "https://example.com/doc"]


def test_build_prompt_block_when_reference_mode_then_shows_pointers(tmp_path) -> None:
    (tmp_path / "lazy-skill.md").write_text(
        "---\nreference_mode: true\nreferences: docs/guide.md\n---\n# Lazy\nShort summary body",
        encoding="utf-8",
    )
    lib = SkillLibrary(skills_dir=tmp_path)
    block = lib.build_prompt_block(["lazy-skill"])
    assert "[reference mode]" in block
    assert "docs/guide.md" in block
    assert "Fetch on demand" in block


@pytest.mark.asyncio
async def test_build_prompt_block_async_when_local_reference_then_inlines_doc(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    doc = tmp_path / "docs"
    doc.mkdir()
    (doc / "guide.md").write_text("# Guide\nFetched instructions", encoding="utf-8")
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "lazy-skill.md").write_text(
        "---\nreference_mode: true\nreferences: docs/guide.md\n---\n# Lazy\nSummary",
        encoding="utf-8",
    )
    lib = SkillLibrary(skills_dir=skills_dir)
    monkeypatch.setattr(
        "app.application.services.supervisor.skill_reference_fetch.resolve_repo_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "app.core.config.settings.skill_lazy_reference_fetch_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.core.config.settings.skill_reference_fetch_max_chars",
        3000,
    )
    block = await lib.build_prompt_block_async(["lazy-skill"], lazy_fetch=True)
    assert "Fetched instructions" in block
    assert "Reference: docs/guide.md" in block


@pytest.mark.asyncio
async def test_fetch_skill_reference_when_local_missing_then_empty(tmp_path) -> None:
    text = await fetch_skill_reference("docs/missing.md", repo_root=tmp_path)
    assert text == ""
