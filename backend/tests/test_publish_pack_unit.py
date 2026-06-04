"""Unit tests for publish pack Phase A validation and archive."""

from __future__ import annotations

import pytest

from app.application.services.publish_pack import (
    PublishPackValidationError,
    extract_publish_pack_json,
    validate_publish_pack,
)


def test_extract_publish_pack_json_from_fence() -> None:
    text = '''
Some prose
```json
{"format": "queenswarm.publish_pack.v1", "artifact_type": "publish_pack", "channel": "instagram", "title": "Hi", "body": "Body text here", "simulate_only": true}
```
'''
    payload = extract_publish_pack_json(text)
    assert payload is not None
    assert payload["artifact_type"] == "publish_pack"


def test_validate_publish_pack_rejects_live_mode() -> None:
    payload = {
        "artifact_type": "publish_pack",
        "channel": "instagram",
        "title": "Test",
        "body": "Hello world",
        "simulate_only": False,
    }
    with pytest.raises(PublishPackValidationError):
        validate_publish_pack(payload)


def test_validate_publish_pack_accepts_simulate() -> None:
    payload = {
        "artifact_type": "publish_pack",
        "channel": "instagram",
        "title": "Test",
        "body": "Hello world",
        "simulate_only": True,
        "snippets": [{"text": "Short post", "hashtags": ["ai"]}],
    }
    pack = validate_publish_pack(payload)
    assert pack.simulate_only is True
    assert pack.snippets[0].text == "Short post"


def test_validate_publish_pack_accepts_linkedin_simulate_channel() -> None:
    payload = {
        "artifact_type": "publish_pack",
        "channel": "LinkedIn",
        "title": "LinkedIn thought leadership pack",
        "body": "A simulate-first LinkedIn pack for B2B SaaS founders.",
        "simulate_only": True,
        "snippets": [{"text": "Founder POV post", "hashtags": ["b2bsaas"]}],
    }
    pack = validate_publish_pack(payload)
    assert pack.channel == "linkedin"


def test_validate_publish_pack_rejects_secrets() -> None:
    payload = {
        "artifact_type": "publish_pack",
        "channel": "instagram",
        "title": "Bad",
        "body": "sk-abcdefghijklmnopqrstuvwxyz1234567890",
        "simulate_only": True,
    }
    with pytest.raises(PublishPackValidationError):
        validate_publish_pack(payload)


def test_validate_publish_pack_merges_video_url_for_tiktok() -> None:
    payload = {
        "artifact_type": "publish_pack",
        "channel": "tiktok",
        "title": "Reel",
        "body": "Caption text",
        "simulate_only": True,
        "video_url": "https://cdn.example.com/clip.mp4",
    }
    pack = validate_publish_pack(payload)
    assert pack.media_url == "https://cdn.example.com/clip.mp4"
