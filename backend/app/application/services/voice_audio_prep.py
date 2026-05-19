"""Normalize browser-captured audio before STT provider upload."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from app.application.services.voice_exceptions import VoiceEmptyTranscriptionError, VoiceServiceError

_STT_CONTAINER_MIMES = frozenset(
    {
        "audio/wav",
        "audio/x-wav",
        "audio/mpeg",
        "audio/mp3",
        "audio/ogg",
        "audio/opus",
        "audio/flac",
        "audio/aac",
        "audio/mp4",
        "audio/m4a",
        "video/mp4",
    },
)

_XAI_FORMAT_LANGUAGES = frozenset(
    {
        "ar",
        "cs",
        "da",
        "de",
        "en",
        "es",
        "fa",
        "fil",
        "fr",
        "hi",
        "id",
        "it",
        "ja",
        "ko",
        "mk",
        "ms",
        "nl",
        "pl",
        "pt",
        "ro",
        "ru",
        "sv",
        "th",
        "tr",
        "vi",
    },
)


def normalize_stt_language(language: str | None) -> str | None:
    """Map UI language codes to xAI STT formatting hints."""

    raw = (language or "").strip().lower()
    if not raw or raw == "auto":
        return None
    code = raw.split("-", 1)[0]
    if code == "sk":
        return "cs"
    if code in _XAI_FORMAT_LANGUAGES:
        return code
    return None


def stt_filename_for_mime(mime_type: str) -> str:
    """Return a filename extension hint for multipart STT uploads."""

    base = mime_type.split(";", 1)[0].strip().lower()
    mapping = {
        "audio/wav": "voice-input.wav",
        "audio/x-wav": "voice-input.wav",
        "audio/mpeg": "voice-input.mp3",
        "audio/mp3": "voice-input.mp3",
        "audio/ogg": "voice-input.ogg",
        "audio/opus": "voice-input.opus",
        "audio/flac": "voice-input.flac",
        "audio/aac": "voice-input.aac",
        "audio/mp4": "voice-input.m4a",
        "audio/m4a": "voice-input.m4a",
        "video/mp4": "voice-input.mp4",
    }
    return mapping.get(base, "voice-input.bin")


async def prepare_stt_audio(
    *,
    audio_bytes: bytes,
    mime_type: str,
) -> tuple[bytes, str, str]:
    """Transcode browser blobs (WebM/OGG) to mono 16 kHz WAV for reliable Grok STT."""

    if len(audio_bytes) < 256:
        raise VoiceEmptyTranscriptionError("Audio chunk too small for transcription.")

    base = mime_type.split(";", 1)[0].strip().lower()
    if base in {"audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3", "audio/flac"}:
        return audio_bytes, base, stt_filename_for_mime(base)

    if base in {
        "audio/webm",
        "video/webm",
        "audio/ogg",
        "audio/opus",
        "application/octet-stream",
        "audio/bin",
        "audio/mp4",
        "audio/m4a",
        "video/mp4",
    }:
        suffix = ".ogg" if base in {"audio/ogg", "audio/opus"} else ".webm"
        if base in {"audio/mp4", "audio/m4a", "video/mp4"}:
            suffix = ".mp4"
        wav_bytes = await _transcode_to_wav(audio_bytes, suffix=suffix)
        return wav_bytes, "audio/wav", "voice-input.wav"

    wav_bytes = await _transcode_to_wav(audio_bytes, suffix=".bin")
    return wav_bytes, "audio/wav", "voice-input.wav"


async def transcode_raw_to_wav(audio_bytes: bytes, *, mime_type: str) -> tuple[bytes, str, str]:
    """Force WAV transcode from raw browser bytes (Grok STT format-recovery retry)."""

    base = mime_type.split(";", 1)[0].strip().lower()
    suffix = ".ogg" if base in {"audio/ogg", "audio/opus"} else ".webm"
    if base in {"audio/mp4", "audio/m4a", "video/mp4"}:
        suffix = ".mp4"
    wav_bytes = await _transcode_to_wav(audio_bytes, suffix=suffix)
    return wav_bytes, "audio/wav", "voice-input.wav"


async def _transcode_to_wav(audio_bytes: bytes, *, suffix: str) -> bytes:
    """Convert arbitrary browser audio to WAV via ffmpeg."""

    with tempfile.TemporaryDirectory(prefix="qs-voice-") as tmp:
        src = Path(tmp) / f"input{suffix}"
        dst = Path(tmp) / "output.wav"
        src.write_bytes(audio_bytes)
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostats",
            "-y",
            "-i",
            str(src),
            "-vn",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            "-f",
            "wav",
            str(dst),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _stdout, stderr = await proc.communicate()
        if proc.returncode != 0 or not dst.exists():
            detail = stderr.decode("utf-8", errors="replace")[:220].strip()
            raise VoiceServiceError(f"Audio transcode failed: {detail or proc.returncode}")
        return dst.read_bytes()
