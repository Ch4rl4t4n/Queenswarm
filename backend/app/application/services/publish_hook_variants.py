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


def _first_sentence(text: str, *, max_len: int = 120) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", cleaned, maxsplit=1)
    sentence = parts[0].strip()
    if len(sentence) > max_len:
        return sentence[: max_len - 1].rstrip() + "…"
    return sentence


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

    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for variant in candidates:
        key = variant.hook.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(variant.model_dump())
        if len(unique) >= max(1, min(max_variants, 8)):
            break

    return unique


__all__ = ["PublishHookVariant", "generate_publish_hook_variants"]
