"""Publish media URL validation — HTTPS-only, channel-aware image/video rules."""

from __future__ import annotations

import re
from typing import Literal
from urllib.parse import urlparse

PublishMediaKind = Literal["image", "video", "unknown"]

_VIDEO_EXTENSIONS: frozenset[str] = frozenset({".mp4", ".webm", ".mov", ".m4v", ".mkv"})
_IMAGE_EXTENSIONS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"})
_VIDEO_HOST_HINTS: frozenset[str] = frozenset(
    {"tiktokcdn", "cloudfront.net", "amazonaws.com", "blob.core.windows.net", "storage.googleapis.com"},
)

_RE_LOCAL_HOST = re.compile(
    r"^(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|0\.0\.0\.0|\[::1\])",
    re.IGNORECASE,
)


def _path_extension(url: str) -> str:
    path = urlparse(url).path.lower()
    dot = path.rfind(".")
    if dot < 0:
        return ""
    return path[dot:]


def classify_publish_media_url(url: str | None) -> PublishMediaKind | None:
    """Classify media URL as image, video, or unknown."""

    text = str(url or "").strip()
    if not text:
        return None
    ext = _path_extension(text)
    if ext in _VIDEO_EXTENSIONS:
        return "video"
    if ext in _IMAGE_EXTENSIONS:
        return "image"
    host = (urlparse(text).hostname or "").lower()
    if any(hint in host for hint in _VIDEO_HOST_HINTS) and ext in {"", ".mp4"}:
        return "video"
    return "unknown"


def is_safe_publish_media_url(url: str | None) -> bool:
    """Return True when URL is HTTPS, has no embedded credentials, and is not private."""

    text = str(url or "").strip()
    if not text or len(text) > 500:
        return False
    try:
        parsed = urlparse(text)
    except ValueError:
        return False
    if parsed.scheme.lower() != "https":
        return False
    if parsed.username or parsed.password:
        return False
    host = (parsed.hostname or "").strip().lower()
    if not host or _RE_LOCAL_HOST.match(host):
        return False
    return True


def validate_publish_media_url(
    url: str | None,
    *,
    channel: str,
    required: bool = False,
) -> tuple[bool, str, PublishMediaKind | None]:
    """Validate media URL for a publish channel.

    Returns:
        (ok, message, media_kind)
    """

    channel_key = str(channel or "").strip().lower()
    text = str(url or "").strip() or None

    if not text:
        if required:
            return False, "TikTok publish requires a public HTTPS video URL in media_url.", None
        return True, "", None

    if not is_safe_publish_media_url(text):
        return False, "media_url must be a public HTTPS URL (no credentials, no localhost).", None

    kind = classify_publish_media_url(text)
    if channel_key == "tiktok":
        if kind == "image":
            return False, "TikTok requires a video file URL (.mp4, .webm, .mov) in media_url.", kind
        if kind not in {"video", "unknown"}:
            return False, "TikTok media_url must point to a video asset.", kind
    if channel_key in {"instagram", "facebook"} and kind == "video":
        return (
            False,
            f"{channel_key} image posts require an image URL — use .jpg/.png/.webp in media_url.",
            kind,
        )
    return True, "", kind


__all__ = [
    "PublishMediaKind",
    "classify_publish_media_url",
    "is_safe_publish_media_url",
    "validate_publish_media_url",
]
