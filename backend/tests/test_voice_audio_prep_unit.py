"""Unit tests for voice audio normalization helpers."""

from __future__ import annotations

import pytest

from app.application.services.voice_audio_prep import normalize_stt_language, prepare_stt_audio
from app.application.services.voice_exceptions import VoiceEmptyTranscriptionError


def test_normalize_stt_language_maps_slovak_to_czech() -> None:
    """Slovak UI language should map to Czech xAI formatting hint."""

    assert normalize_stt_language("sk") == "cs"
    assert normalize_stt_language("sk-SK") == "cs"


def test_normalize_stt_language_auto_is_none() -> None:
    """Auto/empty language should omit explicit STT language hint."""

    assert normalize_stt_language("auto") is None
    assert normalize_stt_language("") is None
    assert normalize_stt_language(None) is None


@pytest.mark.asyncio
async def test_prepare_stt_audio_rejects_tiny_payload() -> None:
    """Sub-256-byte chunks are treated as silent/no-op, not hard failures."""

    with pytest.raises(VoiceEmptyTranscriptionError):
        await prepare_stt_audio(audio_bytes=b"\x00" * 32, mime_type="audio/webm")
