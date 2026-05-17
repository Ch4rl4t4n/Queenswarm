"""Parse orchestrator tri-section Ballroom finale (Phase 0.51)."""

from __future__ import annotations

import json
from typing import Any


def split_orchestrator_deliverable_sections(raw: str) -> dict[str, str | None]:
    """Slice SECTION_TEXT / SECTION_JSON / SECTION_VOICE positional blocks."""

    blob = raw.strip()
    txt_start = blob.find("SECTION_TEXT:")
    json_start = blob.find("SECTION_JSON:")
    voice_start = blob.find("SECTION_VOICE:")

    text = None
    jsn = None
    voice = None

    if txt_start >= 0 and json_start > txt_start:
        text = blob[txt_start + len("SECTION_TEXT:") : json_start].strip() or None
    elif txt_start >= 0 and json_start < 0 and voice_start > txt_start:
        text = blob[txt_start + len("SECTION_TEXT:") : voice_start].strip() or None

    if json_start >= 0:
        json_body_start = json_start + len("SECTION_JSON:")
        if voice_start > json_start:
            jsn = blob[json_body_start:voice_start].strip() or None
        else:
            jsn = blob[json_body_start:].strip() or None

    if voice_start >= 0:
        voice = blob[voice_start + len("SECTION_VOICE:") :].strip() or None

    return {"text": text, "json": jsn, "voice": voice}


def coalesce_json_text(fragment: str | None) -> dict[str, Any]:
    """Parse JSON object substring from orch SECTION_JSON."""

    if not fragment or not fragment.strip():
        return {}
    text = fragment.strip()
    brace = text.find("{")
    end = text.rfind("}")
    if brace < 0 or end <= brace:
        return {}
    try:
        loaded = json.loads(text[brace : end + 1])
        return loaded if isinstance(loaded, dict) else {}
    except json.JSONDecodeError:
        return {}


__all__ = ["coalesce_json_text", "split_orchestrator_deliverable_sections"]
