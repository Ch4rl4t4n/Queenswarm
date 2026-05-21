"""Overnight swarm report TTS — Ballroom voice briefing from Dump & Sleep."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.dump_sleep_service import DumpSleepService
from app.application.services.voice_exceptions import VoiceServiceError
from app.application.services.voice_multimodal import VoiceSynthesisResult, synthesize_speech
from app.core.config import settings

_MAX_SCRIPT_CHARS = 900
_MD_HEADING_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_MD_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_MD_ITALIC_RE = re.compile(r"_([^_]+)_")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_WS_RE = re.compile(r"\s+")


def briefing_markdown_to_script(briefing_md: str, *, max_chars: int = _MAX_SCRIPT_CHARS) -> str:
    """Convert verified briefing markdown into a concise TTS script.

    Args:
        briefing_md: Morning briefing markdown from Dump & Sleep.
        max_chars: Hard cap to keep TTS latency and cost bounded.

    Returns:
        Spoken script suitable for ``synthesize_speech``.
    """

    text = briefing_md.strip()
    if not text:
        return "Good morning. Your overnight swarm report is ready, but the briefing is empty."
    text = _MD_HEADING_RE.sub("", text)
    text = _MD_BOLD_RE.sub(r"\1", text)
    text = _MD_ITALIC_RE.sub(r"\1", text)
    text = _MD_LINK_RE.sub(r"\1", text)
    text = text.replace("- ", "").replace("* ", "")
    text = _WS_RE.sub(" ", text).strip()
    intro = "Good morning. Here is your overnight swarm report. "
    script = f"{intro}{text}"
    limit = max(200, int(max_chars))
    if len(script) <= limit:
        return script
    trimmed = script[: limit - 3].rsplit(" ", 1)[0]
    return f"{trimmed}..."


async def build_overnight_voice_payload(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    window_hours: int | None = None,
) -> dict[str, Any]:
    """Synthesize voice briefing for the latest completed overnight report.

    Args:
        session: Async SQLAlchemy session.
        tenant_id: Tenant scope for batch lookup.
        window_hours: Reporting window override (defaults to settings).

    Returns:
        API payload with optional base64 audio when a briefing exists.
    """

    hours = int(window_hours or settings.dump_sleep_report_window_hours)
    service = DumpSleepService(db=session)
    row = await service.latest_overnight_report(tenant_id=tenant_id, window_hours=hours)
    if row is None or not (row.briefing_md or "").strip():
        return {
            "available": False,
            "batch_id": None,
            "script_text": "",
            "audio_base64": "",
            "content_type": "",
            "provider": "",
            "window_hours": hours,
        }

    script = briefing_markdown_to_script(row.briefing_md or "")
    if not settings.voice_enabled:
        return {
            "available": True,
            "batch_id": row.id,
            "script_text": script,
            "audio_base64": "",
            "content_type": "",
            "provider": "",
            "window_hours": hours,
            "voice_disabled": True,
        }

    audio: VoiceSynthesisResult = await synthesize_speech(
        text=script,
        preferred_provider="auto",
        latency_mode="balanced",
        tts_tone="professional",
    )
    return {
        "available": True,
        "batch_id": row.id,
        "script_text": script,
        "audio_base64": audio.audio_base64,
        "content_type": audio.content_type,
        "provider": audio.provider,
        "window_hours": hours,
        "voice_disabled": False,
    }


__all__ = ["briefing_markdown_to_script", "build_overnight_voice_payload"]
