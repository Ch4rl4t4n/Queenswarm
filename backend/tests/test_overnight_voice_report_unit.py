"""Unit tests for overnight voice report TTS helpers."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.application.services import overnight_voice_report
from app.application.services.voice_multimodal import VoiceSynthesisResult


def test_briefing_markdown_to_script_strips_markdown_and_caps_length() -> None:
    """Markdown headings and emphasis become spoken plain text."""

    md = "# Overnight Swarm Report\n\n- Files received: **2**\n- Pollen earned: **7.5**"
    script = overnight_voice_report.briefing_markdown_to_script(md, max_chars=500)
    assert "Good morning" in script
    assert "Files received" in script
    assert "**" not in script
    assert "#" not in script


@pytest.mark.asyncio
async def test_build_overnight_voice_payload_when_no_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing batch returns unavailable payload without TTS call."""

    class _Svc:
        async def latest_overnight_report(self, **_kwargs: object) -> None:
            return None

    monkeypatch.setattr(overnight_voice_report, "DumpSleepService", lambda **_kw: _Svc())

    payload = await overnight_voice_report.build_overnight_voice_payload(
        session=SimpleNamespace(),
        tenant_id=uuid.uuid4(),
    )
    assert payload["available"] is False
    assert payload["audio_base64"] == ""


@pytest.mark.asyncio
async def test_build_overnight_voice_payload_synthesizes_audio(monkeypatch: pytest.MonkeyPatch) -> None:
    """Completed batch triggers TTS synthesis."""

    row = SimpleNamespace(id=uuid.uuid4(), briefing_md="# Report\n\n- Pollen earned: **3**")

    class _Svc:
        async def latest_overnight_report(self, **_kwargs: object) -> object:
            return row

    async def _fake_tts(**_kwargs: object) -> VoiceSynthesisResult:
        return VoiceSynthesisResult(audio_base64="abc123", content_type="audio/mpeg", provider="openai")

    monkeypatch.setattr(overnight_voice_report, "DumpSleepService", lambda **_kw: _Svc())
    monkeypatch.setattr(overnight_voice_report.settings, "voice_enabled", True)
    monkeypatch.setattr(overnight_voice_report, "synthesize_speech", _fake_tts)

    payload = await overnight_voice_report.build_overnight_voice_payload(
        session=SimpleNamespace(),
        tenant_id=uuid.uuid4(),
    )
    assert payload["available"] is True
    assert payload["audio_base64"] == "abc123"
    assert payload["provider"] == "openai"
    assert "Good morning" in payload["script_text"]
