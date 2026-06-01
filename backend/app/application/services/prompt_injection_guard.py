"""Lightweight prompt-injection heuristics for untrusted ingest (Hermes-style guard)."""

from __future__ import annotations

import re
from dataclasses import dataclass

_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I),
    re.compile(r"disregard\s+(your|the)\s+(system|developer)\s+prompt", re.I),
    re.compile(r"you\s+are\s+now\s+(?:in\s+)?(?:DAN|jailbreak|unrestricted)\s+mode", re.I),
    re.compile(r"<\s*/?\s*system\s*>", re.I),
    re.compile(r"\[INST\]|\[/INST\]", re.I),
    re.compile(r"BEGIN\s+SECRET\s+INSTRUCTIONS", re.I),
    re.compile(r"do\s+not\s+tell\s+the\s+user", re.I),
)


@dataclass(frozen=True, slots=True)
class PromptInjectionScanResult:
    """Outcome of scanning untrusted text before LLM ingest."""

    blocked: bool
    reason: str | None = None
    matched_pattern: str | None = None


def scan_untrusted_text(text: str, *, max_scan_chars: int = 12_000) -> PromptInjectionScanResult:
    """Return blocked=True when common injection markers are detected."""

    blob = (text or "")[:max_scan_chars]
    if not blob.strip():
        return PromptInjectionScanResult(blocked=False)

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(blob):
            return PromptInjectionScanResult(
                blocked=True,
                reason="Untrusted content matched prompt-injection heuristics.",
                matched_pattern=pattern.pattern,
            )
    return PromptInjectionScanResult(blocked=False)


def sanitize_untrusted_text(text: str, *, max_scan_chars: int = 12_000) -> tuple[str, PromptInjectionScanResult]:
    """Scan and replace blocked ingest with a safe operator-visible stub."""

    scan = scan_untrusted_text(text, max_scan_chars=max_scan_chars)
    if scan.blocked:
        return (
            "[BLOCKED: potential prompt injection in external content — operator review required.]",
            scan,
        )
    return text, scan


__all__ = ["PromptInjectionScanResult", "sanitize_untrusted_text", "scan_untrusted_text"]
