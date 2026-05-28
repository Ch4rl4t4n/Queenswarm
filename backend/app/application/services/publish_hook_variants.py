"""Publish hook variants — deterministic A/B hooks for social packs (no LLM required)."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PublishHookVariant(BaseModel):
    """One alternate opening hook for a publish pack."""

    model_config = ConfigDict(extra="forbid")

    id: str
    style: str
    hook: str = Field(max_length=280)
    rationale: str = Field(default="", max_length=200)
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


_CHANNEL_STYLE_WEIGHT: dict[str, dict[str, float]] = {
    "instagram": {"curiosity": 0.84, "number": 0.78, "question": 0.76, "bold": 0.82, "cta": 0.86},
    "facebook": {"curiosity": 0.78, "number": 0.8, "question": 0.74, "bold": 0.77, "cta": 0.81},
    "twitter": {"curiosity": 0.8, "number": 0.75, "question": 0.73, "bold": 0.79, "thread": 0.9},
    "x": {"curiosity": 0.8, "number": 0.75, "question": 0.73, "bold": 0.79, "thread": 0.9},
    "tiktok": {"curiosity": 0.76, "number": 0.78, "question": 0.77, "bold": 0.81, "pov": 0.91},
    "newsletter": {"curiosity": 0.74, "number": 0.81, "question": 0.72, "bold": 0.78, "cta": 0.7},
}


def _first_sentence(text: str, *, max_len: int = 120) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", cleaned, maxsplit=1)
    sentence = parts[0].strip()
    if len(sentence) > max_len:
        return sentence[: max_len - 1].rstrip() + "…"
    return sentence


def _style_weight(*, channel: str, style: str) -> float:
    per_channel = _CHANNEL_STYLE_WEIGHT.get(channel.lower()) or {}
    return float(per_channel.get(style.lower(), 0.72))


def _text_quality_score(hook: str, *, channel: str) -> float:
    text = hook.strip()
    if not text:
        return 0.0
    max_len = 280 if channel.lower() in {"twitter", "x"} else 200
    length_ratio = min(1.0, len(text) / max_len)
    length_score = 1.0 - abs(length_ratio - 0.55)
    punctuation_bonus = 0.06 if ("?" in text or "!" in text) else 0.0
    emoji_bonus = 0.04 if any(ch in text for ch in ("🧵", "🔥", "🚀")) else 0.0
    return max(0.0, min(1.0, 0.7 * length_score + punctuation_bonus + emoji_bonus))


def score_publish_hook_variant(*, channel: str, style: str, hook: str) -> tuple[float, float]:
    """Return deterministic score + confidence for one variant."""

    style_score = _style_weight(channel=channel, style=style)
    quality_score = _text_quality_score(hook, channel=channel)
    score = max(0.0, min(1.0, 0.65 * style_score + 0.35 * quality_score))
    confidence = max(0.0, min(1.0, 0.75 * score + 0.2 * style_score))
    return round(score, 3), round(confidence, 3)


def generate_publish_hook_variants(
    *,
    title: str,
    body: str,
    channel: str = "instagram",
    max_variants: int = 5,
) -> list[dict[str, Any]]:
    """Build hook variants from pack title/body using proven short-form patterns."""

    title_clean = title.strip()[:120]
    body_clean = body.strip()
    lead = _first_sentence(body_clean, max_len=100)
    ch = channel.lower()

    candidates: list[PublishHookVariant] = []

    if title_clean:
        candidates.append(
            PublishHookVariant(
                id="curiosity",
                style="curiosity",
                hook=f"Most people miss this about {title_clean} — here's what changed.",
                rationale="Curiosity gap from title",
            ),
        )
        candidates.append(
            PublishHookVariant(
                id="number",
                style="number",
                hook=f"3 lessons from {title_clean} (the 2nd one surprised me).",
                rationale="Number + listicle hook",
            ),
        )
        candidates.append(
            PublishHookVariant(
                id="question",
                style="question",
                hook=f"What if {title_clean.lower()} took 10 minutes instead of 10 hours?",
                rationale="Question reframe",
            ),
        )

    if lead:
        candidates.append(
            PublishHookVariant(
                id="bold",
                style="bold",
                hook=lead if len(lead) <= 200 else lead[:197] + "…",
                rationale="Lead sentence as hook",
            ),
        )

    if ch == "tiktok":
        candidates.append(
            PublishHookVariant(
                id="tiktok_pov",
                style="pov",
                hook=f"POV: you finally figured out {title_clean or 'this'}",
                rationale="TikTok POV pattern",
            ),
        )
    elif ch in {"twitter", "x"}:
        candidates.append(
            PublishHookVariant(
                id="thread",
                style="thread",
                hook=f"🧵 {title_clean or lead or 'Quick thread'}",
                rationale="Thread opener",
            ),
        )
    else:
        candidates.append(
            PublishHookVariant(
                id="cta",
                style="cta",
                hook=f"Save this if you're working on {title_clean or 'growth'} this week.",
                rationale="Save/share CTA hook",
            ),
        )

    scored_candidates: list[PublishHookVariant] = []
    for variant in candidates:
        score, confidence = score_publish_hook_variant(
            channel=ch,
            style=variant.style,
            hook=variant.hook,
        )
        scored_candidates.append(
            variant.model_copy(
                update={
                    "score": score,
                    "confidence": confidence,
                },
            ),
        )

    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    ranked = sorted(
        scored_candidates,
        key=lambda item: (item.score, item.confidence, len(item.hook)),
        reverse=True,
    )
    for variant in ranked:
        key = variant.hook.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(variant.model_dump())
        if len(unique) >= max(1, min(max_variants, 8)):
            break

    return unique


__all__ = ["PublishHookVariant", "generate_publish_hook_variants", "score_publish_hook_variant"]
