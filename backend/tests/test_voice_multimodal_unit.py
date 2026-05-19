"""Unit tests for voice_multimodal STT provider wiring."""

from __future__ import annotations

import base64
import io

import pytest

from app.application.services import voice_multimodal
from app.application.services.voice_exceptions import VoiceServiceError


@pytest.mark.asyncio
async def test_grok_stt_uploads_file_like_object_not_raw_tuple(monkeypatch: pytest.MonkeyPatch) -> None:
    """Grok STT must pass a readable file object to httpx, not a nested tuple."""

    monkeypatch.setattr(voice_multimodal.settings, "voice_enabled", True)
    monkeypatch.setattr(voice_multimodal, "provider_effective_grok", lambda: "grok-test-key")
    monkeypatch.setattr(voice_multimodal, "provider_effective_deepgram", lambda: None)
    monkeypatch.setattr(voice_multimodal, "provider_effective_openai", lambda: None)

    async def _fake_prepare(*, audio_bytes: bytes, mime_type: str) -> tuple[bytes, str, str]:
        assert mime_type == "audio/webm"
        return audio_bytes, "audio/wav", "chunk.wav"

    monkeypatch.setattr(voice_multimodal, "prepare_stt_audio", _fake_prepare)

    captured: dict[str, object] = {}

    class _FakeResponse:
        status_code = 200
        text = ""

        def json(self) -> dict[str, object]:
            return {"text": "ahoj funguješ"}

    class _FakeClient:
        async def __aenter__(self) -> _FakeClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, url: str, **kwargs: object) -> _FakeResponse:
            captured["url"] = url
            captured["data"] = kwargs.get("data")
            captured["files"] = kwargs.get("files")
            return _FakeResponse()

    monkeypatch.setattr(voice_multimodal.httpx, "AsyncClient", lambda **kwargs: _FakeClient())

    payload = base64.b64encode(b"\x00" * 4096).decode("ascii")
    out = await voice_multimodal.transcribe_audio(
        audio_base64=payload,
        mime_type="audio/webm",
        language="sk",
        preferred_provider="grok",
    )

    assert out.text == "ahoj funguješ"
    assert out.provider == "grok_stt"
    files = captured.get("files")
    assert isinstance(files, dict)
    file_entry = files.get("file")
    assert isinstance(file_entry, tuple)
    assert len(file_entry) == 3
    _name, file_obj, mime = file_entry
    assert isinstance(file_obj, io.BytesIO)
    assert mime == "audio/wav"
    data = captured.get("data")
    assert isinstance(data, dict)
    assert data.get("language") == "cs"


@pytest.mark.asyncio
async def test_stt_raises_when_all_providers_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """When every provider errors, surface a consolidated VoiceServiceError."""

    monkeypatch.setattr(voice_multimodal.settings, "voice_enabled", True)
    monkeypatch.setattr(voice_multimodal, "provider_effective_grok", lambda: "grok-key")
    monkeypatch.setattr(voice_multimodal, "provider_effective_deepgram", lambda: None)
    monkeypatch.setattr(voice_multimodal, "provider_effective_openai", lambda: None)

    async def _fake_prepare(*, audio_bytes: bytes, mime_type: str) -> tuple[bytes, str, str]:
        return audio_bytes, "audio/wav", "chunk.wav"

    monkeypatch.setattr(voice_multimodal, "prepare_stt_audio", _fake_prepare)

    class _FailResponse:
        status_code = 500
        text = "upstream failed"

        def json(self) -> dict[str, object]:
            return {}

    class _FailClient:
        async def __aenter__(self) -> _FailClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, *args: object, **kwargs: object) -> _FailResponse:
            return _FailResponse()

    monkeypatch.setattr(voice_multimodal.httpx, "AsyncClient", lambda **kwargs: _FailClient())

    payload = base64.b64encode(b"\x00" * 4096).decode("ascii")
    with pytest.raises(VoiceServiceError, match="Grok STT failure"):
        await voice_multimodal.transcribe_audio(
            audio_base64=payload,
            mime_type="audio/webm",
            preferred_provider="grok",
        )
