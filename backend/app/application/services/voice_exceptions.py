"""Voice pipeline exception types."""

from __future__ import annotations


class VoiceServiceError(RuntimeError):
    """Raised when voice provider interaction fails."""


class VoiceEmptyTranscriptionError(VoiceServiceError):
    """Audio chunk had no detectable speech — safe to skip without operator alert."""
