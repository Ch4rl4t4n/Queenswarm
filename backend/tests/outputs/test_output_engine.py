"""Phase 0.51 — deterministic tests for parsing helpers and scaffolding."""

from __future__ import annotations

from app.domain.outputs.engine import OutputEngine, build_fallback_structured
from app.domain.outputs.parsing import coalesce_json_text, split_orchestrator_deliverable_sections
from app.domain.outputs.service import derive_title, slugify_fragment


def test_split_orchestrator_deliverable_sections_all_three() -> None:
    raw = """
SECTION_TEXT:
# Hello

Body here.

SECTION_JSON:
{"found": true, "score": 0.9}

SECTION_VOICE:
Brief voice line.
"""

    parts = split_orchestrator_deliverable_sections(raw)
    assert parts["text"] is not None and "# Hello" in parts["text"]
    assert parts["json"] is not None and '"found"' in parts["json"]
    assert parts["voice"] == "Brief voice line."


def test_coalesce_json_extracts_object_from_noise() -> None:
    fragment = 'noise {"tier": "gold", "n": [1]} tail'
    out = coalesce_json_text(fragment)
    assert out["tier"] == "gold"
    assert out["n"] == [1]


def test_coalesce_json_empty_returns_empty_dict() -> None:
    assert coalesce_json_text(None) == {}
    assert coalesce_json_text("{}") == {}


def test_derive_title_prefers_top_level_heading() -> None:
    md = "# Real headline\n\n### Nested detail\nParagraph."
    assert derive_title(md, "fallback") == "Real headline"


def test_slugify_all_punctuation_falls_back() -> None:
    assert slugify_fragment("@@@") == "deliverable"


def test_slugify_truncates() -> None:
    long_slug = "word-" * 40
    out = slugify_fragment(long_slug, max_len=20)
    assert len(out) <= 20


def test_build_fallback_structured_caps_and_shape() -> None:
    excerpt = "x" * 4000
    out = build_fallback_structured(brief_excerpt=excerpt, manager_slugs=["m1"], post_meta={"ok": 1})

    assert out["format"] == "queenswarm.final_deliverable.v1"
    assert len(out["brief_excerpt"]) == 2000
    assert out["manager_templates"] == ["m1"]
    assert out["reflection"]["post_mortem"] == {"ok": 1}


def test_output_engine_public_api_surface() -> None:
    """Guard against accidental renaming of façade entrypoints."""

    assert callable(OutputEngine.create_final_deliverable)
    assert callable(OutputEngine.regenerate_via_llm)
