"""Voice and multimodal helpers (STT/TTS) for Ballroom and supervisor control."""

from __future__ import annotations

import asyncio
import base64
import io
from dataclasses import dataclass
from typing import Literal

import httpx

from app.application.services.llm_runtime_credentials import (
    provider_effective_deepgram,
    provider_effective_elevenlabs,
    provider_effective_grok,
    provider_effective_openai,
)
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


from app.application.services.voice_audio_prep import (
    normalize_stt_language,
    prepare_stt_audio,
    stt_filename_for_mime,
    transcode_raw_to_wav,
)
from app.application.services.voice_exceptions import VoiceEmptyTranscriptionError, VoiceServiceError

__all__ = [
    "VoiceEmptyTranscriptionError",
    "VoiceServiceError",
    "VoiceSynthesisResult",
    "VoiceTranscriptionResult",
    "synthesize_speech",
    "transcribe_audio",
]


def _decode_audio(payload_base64: str) -> bytes:
    try:
        return base64.b64decode(payload_base64, validate=True)
    except Exception as exc:  # noqa: BLE001
        msg = f"Invalid base64 audio payload: {exc!s}"
        raise VoiceServiceError(msg) from exc


def _empty_transcription_error(*, provider: str, audio_bytes: bytes, body: dict[str, object]) -> VoiceEmptyTranscriptionError:
    duration_raw = body.get("duration")
    duration = float(duration_raw) if isinstance(duration_raw, (int, float)) else None
    if len(audio_bytes) < 2048 or (duration is not None and duration < 0.35):
        return VoiceEmptyTranscriptionError(f"{provider} returned no speech in audio chunk.")
    return VoiceEmptyTranscriptionError(f"{provider} heard audio but returned no words — speak louder or check language settings.")


async def transcribe_audio(
    *,
    audio_base64: str,
    mime_type: str,
    language: str | None = None,
    preferred_provider: Literal["auto", "grok", "deepgram", "openai"] = "auto",
    latency_mode: Literal["balanced", "fast"] = "balanced",
) -> VoiceTranscriptionResult:
    """Transcribe audio via Grok (preferred), Deepgram, or OpenAI Whisper."""

    del latency_mode  # reserved — STT always uses WAV transcode for reliability

    if not settings.voice_enabled:
        raise VoiceServiceError("Voice pipeline is disabled by configuration.")
    audio_bytes = _decode_audio(audio_base64)
    try:
        prepared_bytes, prepared_mime, prepared_name = await prepare_stt_audio(
            audio_bytes=audio_bytes,
            mime_type=mime_type,
        )
    except VoiceEmptyTranscriptionError:
        raise
    except VoiceServiceError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise VoiceServiceError(f"Audio prepare failed: {exc!s}") from exc

    deepgram_key = provider_effective_deepgram()
    grok_key = provider_effective_grok()
    openai_key = provider_effective_openai()
    provider_order: list[Literal["grok", "deepgram", "openai"]]
    if preferred_provider == "grok":
        provider_order = ["grok"]
    elif preferred_provider == "deepgram":
        provider_order = ["deepgram"]
    elif preferred_provider == "openai":
        provider_order = ["openai"]
    else:
        provider_order = ["grok", "deepgram", "openai"]

    errors: list[str] = []
    filename = prepared_name
    stt_mime = prepared_mime

    for provider in provider_order:
        if provider == "grok" and grok_key:
            try:
                lang = normalize_stt_language(language)
                upload_bytes = prepared_bytes
                upload_mime = prepared_mime
                upload_name = prepared_name

                async def _grok_stt_attempt(
                    *,
                    with_lang: bool,
                    file_bytes: bytes,
                    file_name: str,
                    file_mime: str,
                ) -> tuple[str, dict[str, object], httpx.Response]:
                    grok_form: dict[str, str] = {}
                    if with_lang and lang:
                        grok_form["language"] = lang
                        grok_form["format"] = "true"

                    async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=4.0)) as client:
                        response = await client.post(
                            "https://api.x.ai/v1/stt",
                            headers={"Authorization": f"Bearer {grok_key}"},
                            data=grok_form or None,
                            files={"file": (file_name, io.BytesIO(file_bytes), file_mime)},
                        )
                    if response.status_code >= 400:
                        return "", {}, response
                    body_obj = response.json()
                    if not isinstance(body_obj, dict):
                        body_obj = {}
                    text_out = str(body_obj.get("text") or "").strip()
                    return text_out, body_obj, response

                text, body, response = await _grok_stt_attempt(
                    with_lang=True,
                    file_bytes=upload_bytes,
                    file_name=upload_name,
                    file_mime=upload_mime,
                )
                if response.status_code >= 400 and "audio format" in response.text.lower():
                    upload_bytes, upload_mime, upload_name = await transcode_raw_to_wav(
                        audio_bytes,
                        mime_type=mime_type,
                    )
                    text, body, response = await _grok_stt_attempt(
                        with_lang=True,
                        file_bytes=upload_bytes,
                        file_name=upload_name,
                        file_mime=upload_mime,
                    )
                if response.status_code >= 400:
                    raise VoiceServiceError(f"Grok STT failure: {response.status_code} {response.text[:220]}")
                if not text and lang:
                    text, body, response = await _grok_stt_attempt(
                        with_lang=False,
                        file_bytes=upload_bytes,
                        file_name=upload_name,
                        file_mime=upload_mime,
                    )
                    if response.status_code >= 400:
                        raise VoiceServiceError(f"Grok STT failure: {response.status_code} {response.text[:220]}")
                if not text:
                    raise _empty_transcription_error(provider="Grok", audio_bytes=upload_bytes, body=body)
                return VoiceTranscriptionResult(text=text, provider="grok_stt", language=language)
            except VoiceEmptyTranscriptionError:
                raise
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))
                continue

        if provider == "deepgram" and deepgram_key:
            try:
                params = {
                    "model": settings.voice_stt_model_deepgram,
                    "smart_format": "true",
                    "punctuate": "true",
                }
                lang = normalize_stt_language(language)
                if lang:
                    params["language"] = lang
                async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=8.0)) as client:
                    response = await client.post(
                        "https://api.deepgram.com/v1/listen",
                        headers={
                            "Authorization": f"Token {deepgram_key}",
                            "Content-Type": stt_mime,
                        },
                        params=params,
                        content=prepared_bytes,
                    )
                if response.status_code >= 400:
                    raise VoiceServiceError(f"Deepgram STT failure: {response.status_code} {response.text[:220]}")
                body = response.json()
                text = str(
                    (
                        body.get("results", {})
                        .get("channels", [{}])[0]
                        .get("alternatives", [{}])[0]
                        .get("transcript")
                    )
                    or "",
                ).strip()
                if not text:
                    raise VoiceEmptyTranscriptionError("Deepgram returned no speech in audio chunk.")
                return VoiceTranscriptionResult(text=text, provider="deepgram", language=language)
            except VoiceEmptyTranscriptionError:
                raise
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))
                continue

        if provider == "openai" and openai_key:
            try:
                openai_name = stt_filename_for_mime(stt_mime)
                data: dict[str, str] = {
                    "model": settings.voice_stt_model,
                    "response_format": "json",
                }
                lang = normalize_stt_language(language)
                if lang:
                    data["language"] = lang

                def _post_openai_stt() -> httpx.Response:
                    with httpx.Client(timeout=httpx.Timeout(30.0, connect=8.0)) as client:
                        return client.post(
                            "https://api.openai.com/v1/audio/transcriptions",
                            headers={"Authorization": f"Bearer {openai_key}"},
                            data=data,
                            files={"file": (openai_name, io.BytesIO(prepared_bytes), stt_mime)},
                        )

                response = await asyncio.to_thread(_post_openai_stt)
                if response.status_code >= 400:
                    raise VoiceServiceError(f"OpenAI STT failure: {response.status_code} {response.text[:220]}")
                body = response.json()
                text = str(body.get("text") or "").strip()
                if not text:
                    raise VoiceEmptyTranscriptionError("OpenAI returned no speech in audio chunk.")
                return VoiceTranscriptionResult(text=text, provider="openai_whisper", language=language)
            except VoiceEmptyTranscriptionError:
                raise
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))
                continue

    if not (grok_key or deepgram_key or openai_key):
        raise VoiceServiceError("No STT provider configured (Grok/Deepgram/OpenAI).")
    detail = "; ".join(errors[:3]) if errors else "all configured STT providers failed"
    if len(provider_order) == 1:
        raise VoiceServiceError(errors[0] if errors else f"{provider_order[0]} STT failed.")
    raise VoiceServiceError(f"STT failed after fallback chain: {detail}")


async def synthesize_speech(
    *,
    text: str,
    preferred_provider: Literal["auto", "grok", "elevenlabs", "openai"] = "auto",
    latency_mode: Literal["balanced", "fast"] = "balanced",
    tts_voice_id: str | None = None,
    tts_language: str | None = None,
    tts_tone: str | None = None,
) -> VoiceSynthesisResult:
    """Synthesize speech via ElevenLabs or OpenAI fallback."""

    if not settings.voice_enabled:
        raise VoiceServiceError("Voice pipeline is disabled by configuration.")
    clipped = text.strip()[:3000]
    if not clipped:
        raise VoiceServiceError("TTS text is empty.")

    eleven_key = provider_effective_elevenlabs()
    grok_key = provider_effective_grok()
    openai_key = provider_effective_openai()
    provider_order: list[Literal["grok", "elevenlabs", "openai"]]
    if preferred_provider == "grok":
        provider_order = ["grok"]
    elif preferred_provider == "elevenlabs":
        provider_order = ["elevenlabs"]
    elif preferred_provider == "openai":
        provider_order = ["openai"]
    else:
        provider_order = ["grok", "elevenlabs", "openai"]

    errors: list[str] = []
    canonical_voice = {
        "ara": "Ara",
        "eve": "Eve",
        "leo": "Leo",
        "rex": "Rex",
        "sal": "Sal",
    }
    voice_from_tone = {
        "warm": "Ara",
        "casual": "Eve",
        "professional": "Rex",
        "friendly": "Sal",
        "authoritative": "Leo",
        "expressive": "Eve",
    }
    tone_clean = (tts_tone or "none").strip().lower()
    requested_voice = (tts_voice_id or "").strip()
    if not requested_voice or requested_voice == "auto":
        requested_voice = voice_from_tone.get(tone_clean, settings.voice_tts_xai_voice_id).strip()
    requested_voice = canonical_voice.get(requested_voice.lower(), requested_voice)
    requested_language = (tts_language or settings.voice_tts_xai_language).strip() or settings.voice_tts_xai_language

    for provider in provider_order:
        if provider == "grok" and grok_key:
            try:
                payload: dict[str, object] = {
                    "text": clipped,
                    "voice_id": requested_voice,
                    "language": requested_language,
                }
                payload["optimize_streaming_latency"] = (
                    1 if latency_mode == "fast" else settings.voice_tts_xai_optimize_streaming_latency
                )
                if settings.voice_tts_xai_output_codec:
                    payload["output_format"] = {
                        "codec": settings.voice_tts_xai_output_codec,
                        "sample_rate": settings.voice_tts_xai_sample_rate,
                        "bit_rate": settings.voice_tts_xai_bit_rate,
                    }
                async with httpx.AsyncClient(timeout=httpx.Timeout(35.0, connect=8.0)) as client:
                    response = await client.post(
                        "https://api.x.ai/v1/tts",
                        headers={
                            "Authorization": f"Bearer {grok_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                if response.status_code >= 400:
                    raise VoiceServiceError(f"Grok TTS failure: {response.status_code} {response.text[:220]}")
                return VoiceSynthesisResult(
                    audio_base64=base64.b64encode(response.content).decode("ascii"),
                    content_type="audio/mpeg",
                    provider="grok_tts",
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))
                continue

        if provider == "elevenlabs" and eleven_key:
            try:
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
                    raise VoiceServiceError(f"ElevenLabs failure: {response.status_code} {response.text[:220]}")
                return VoiceSynthesisResult(
                    audio_base64=base64.b64encode(response.content).decode("ascii"),
                    content_type="audio/mpeg",
                    provider="elevenlabs",
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))
                continue

        if provider == "openai" and openai_key:
            try:
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
                            "Authorization": f"Bearer {openai_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                if response.status_code >= 400:
                    raise VoiceServiceError(f"OpenAI TTS failure: {response.status_code} {response.text[:220]}")
                return VoiceSynthesisResult(
                    audio_base64=base64.b64encode(response.content).decode("ascii"),
                    content_type="audio/mpeg",
                    provider="openai_tts",
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))
                continue

    if not (grok_key or eleven_key or openai_key):
        raise VoiceServiceError("No TTS provider configured (Grok/ElevenLabs/OpenAI).")
    detail = "; ".join(errors[:3]) if errors else "all configured TTS providers failed"
    raise VoiceServiceError(f"TTS failed after fallback chain: {detail}")
