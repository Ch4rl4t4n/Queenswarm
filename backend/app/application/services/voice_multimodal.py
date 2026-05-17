"""Voice and multimodal helpers (STT/TTS) for Ballroom and supervisor control."""

from __future__ import annotations

import base64
from dataclasses import dataclass

import httpx

from app.application.services.llm_runtime_credentials import provider_effective_openai
from app.core.config import settings


@dataclass(slots=True)
class VoiceTranscriptionResult:
    text: str
    provider: str
    language: str | None


@dataclass(slots=True)
class VoiceSynthesisResult:
    audio_base64: str
    content_type: str
    provider: str


class VoiceServiceError(RuntimeError):
    """Raised when voice provider interaction fails."""


def _decode_audio(payload_base64: str) -> bytes:
    try:
        return base64.b64decode(payload_base64, validate=True)
    except Exception as exc:  # noqa: BLE001
        msg = f"Invalid base64 audio payload: {exc!s}"
        raise VoiceServiceError(msg) from exc


async def transcribe_audio(
    *,
    audio_base64: str,
    mime_type: str,
    language: str | None = None,
) -> VoiceTranscriptionResult:
    """Transcribe audio via Whisper-compatible provider."""

    if not settings.voice_enabled:
        raise VoiceServiceError("Voice pipeline is disabled by configuration.")
    api_key = provider_effective_openai()
    if not api_key:
        raise VoiceServiceError("OpenAI key is missing for voice transcription.")
    audio_bytes = _decode_audio(audio_base64)
    filename = "voice-input.webm"
    if "wav" in mime_type:
        filename = "voice-input.wav"
    elif "mpeg" in mime_type or "mp3" in mime_type:
        filename = "voice-input.mp3"
    data: dict[str, str] = {
        "model": settings.voice_stt_model,
        "response_format": "json",
    }
    if language:
        data["language"] = language
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=8.0)) as client:
        response = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            data=data,
            files={"file": (filename, audio_bytes, mime_type)},
        )
    if response.status_code >= 400:
        raise VoiceServiceError(f"STT provider failure: {response.status_code} {response.text[:400]}")
    body = response.json()
    text = str(body.get("text") or "").strip()
    if not text:
        raise VoiceServiceError("Transcription provider returned empty text.")
    return VoiceTranscriptionResult(
        text=text,
        provider="openai_whisper",
        language=language,
    )


async def synthesize_speech(
    *,
    text: str,
) -> VoiceSynthesisResult:
    """Synthesize speech via ElevenLabs or OpenAI fallback."""

    if not settings.voice_enabled:
        raise VoiceServiceError("Voice pipeline is disabled by configuration.")
    clipped = text.strip()[:3000]
    if not clipped:
        raise VoiceServiceError("TTS text is empty.")

    eleven_key = (settings.elevenlabs_api_key or "").strip()
    if eleven_key:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}"
        payload = {
            "text": clipped,
            "model_id": settings.voice_tts_model,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.7},
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(35.0, connect=8.0)) as client:
            response = await client.post(
                url,
                headers={
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": eleven_key,
                },
                json=payload,
            )
        if response.status_code >= 400:
            raise VoiceServiceError(f"ElevenLabs failure: {response.status_code} {response.text[:300]}")
        return VoiceSynthesisResult(
            audio_base64=base64.b64encode(response.content).decode("ascii"),
            content_type="audio/mpeg",
            provider="elevenlabs",
        )

    api_key = provider_effective_openai()
    if not api_key:
        raise VoiceServiceError("No TTS provider configured (ElevenLabs/OpenAI).")
    payload = {
        "model": settings.voice_tts_model_openai,
        "voice": settings.voice_tts_openai_voice,
        "input": clipped,
        "format": "mp3",
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=8.0)) as client:
        response = await client.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
    if response.status_code >= 400:
        raise VoiceServiceError(f"OpenAI TTS failure: {response.status_code} {response.text[:300]}")
    return VoiceSynthesisResult(
        audio_base64=base64.b64encode(response.content).decode("ascii"),
        content_type="audio/mpeg",
        provider="openai_tts",
    )
