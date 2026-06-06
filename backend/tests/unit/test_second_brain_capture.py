"""Unit tests for second-brain capture + connection synthesizer."""

from __future__ import annotations

from types import SimpleNamespace

from app.application.services.second_brain_capture import (
    build_capture_markdown,
    is_capture_note,
    parse_capture_fields,
)
from app.application.services.wiki_connection_synthesizer import (
    compile_connection_intelligence,
    compile_maps_of_content,
)


def test_build_and_parse_capture_roundtrip() -> None:
    md = build_capture_markdown(
        idea="Newsletter loop for indie hackers",
        connects_to=["seo-pipeline", "factory-queue"],
        might_use_for="Skill Factory launch queue",
        key_tension="Speed vs quality on critic gate",
        body="Extra operator notes.",
    )
    assert is_capture_note(md) is True
    fields = parse_capture_fields(md)
    assert "Newsletter loop" in fields["idea"]
    assert "seo-pipeline" in fields["connects_to"]
    assert "Skill Factory" in fields["might_use_for"]
    assert "critic gate" in fields["key_tension"]


def test_compile_moc_and_connections_from_captures() -> None:
    row_a = SimpleNamespace(
        id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        content_text=build_capture_markdown(
            idea="SEO blog pipeline",
            connects_to=["newsletter"],
            might_use_for="Gumroad harness",
            key_tension="Depth vs ship speed",
        ),
        topic_tags=["second_brain:capture", "seo", "factory"],
    )
    row_b = SimpleNamespace(
        id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        content_text=build_capture_markdown(
            idea="Newsletter growth loop",
            connects_to=["seo-pipeline"],
            might_use_for="Launch queue",
            key_tension="Automation vs voice",
        ),
        topic_tags=["second_brain:capture", "seo", "newsletter"],
    )
    moc = compile_maps_of_content([row_a, row_b])
    assert "Maps of Content" in moc
    assert "seo" in moc.lower()
    intel = compile_connection_intelligence([row_a, row_b])
    assert "Connection intelligence" in intel
    assert "Key tensions" in intel
