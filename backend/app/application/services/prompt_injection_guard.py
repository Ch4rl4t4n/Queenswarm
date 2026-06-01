"""Lightweight prompt-injection heuristics — Hermes-style 3-checkpoint model."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from app.core.logging import get_logger

_logger = get_logger(__name__)


class InjectionCheckpoint(StrEnum):
    """Where untrusted text enters the hive pipeline."""

    OPERATOR_INPUT = "operator_input"
    EXTERNAL_TOOL = "external_tool"
    AGENT_OUTPUT = "agent_output"


class PromptInjectionViolationError(ValueError):
    """Raised when operator-supplied text matches injection heuristics (checkpoint 1)."""


_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I),
    re.compile(r"disregard\s+(your|the)\s+(system|developer)\s+prompt", re.I),
    re.compile(r"you\s+are\s+now\s+(?:in\s+)?(?:DAN|jailbreak|unrestricted)\s+mode", re.I),
    re.compile(r"<\s*/?\s*system\s*>", re.I),
    re.compile(r"\[INST\]|\[/INST\]", re.I),
    re.compile(r"BEGIN\s+SECRET\s+INSTRUCTIONS", re.I),
    re.compile(r"do\s+not\s+tell\s+the\s+user", re.I),
)

_OUTPUT_LEAK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"system\s+prompt\s*:", re.I),
    re.compile(r"developer\s+message\s*:", re.I),
    re.compile(r"<\s*instructions\s*>", re.I),
)


@dataclass(frozen=True, slots=True)
class PromptInjectionScanResult:
    """Outcome of scanning untrusted text before LLM ingest."""

    blocked: bool
    checkpoint: InjectionCheckpoint
    reason: str | None = None
    matched_pattern: str | None = None


def scan_untrusted_text(
    text: str,
    *,
    checkpoint: InjectionCheckpoint = InjectionCheckpoint.EXTERNAL_TOOL,
    max_scan_chars: int = 12_000,
) -> PromptInjectionScanResult:
    """Return blocked=True when common injection markers are detected."""

    blob = (text or "")[:max_scan_chars]
    if not blob.strip():
        return PromptInjectionScanResult(blocked=False, checkpoint=checkpoint)

    patterns = _INJECTION_PATTERNS
    if checkpoint == InjectionCheckpoint.AGENT_OUTPUT:
        patterns = (*_INJECTION_PATTERNS, *_OUTPUT_LEAK_PATTERNS)

    for pattern in patterns:
        if pattern.search(blob):
            return PromptInjectionScanResult(
                blocked=True,
                checkpoint=checkpoint,
                reason="Untrusted content matched prompt-injection heuristics.",
                matched_pattern=pattern.pattern,
            )
    return PromptInjectionScanResult(blocked=False, checkpoint=checkpoint)


def sanitize_untrusted_text(
    text: str,
    *,
    checkpoint: InjectionCheckpoint = InjectionCheckpoint.EXTERNAL_TOOL,
    max_scan_chars: int = 12_000,
) -> tuple[str, PromptInjectionScanResult]:
    """Scan and replace blocked ingest with a safe operator-visible stub (checkpoint 2/3)."""

    scan = scan_untrusted_text(text, checkpoint=checkpoint, max_scan_chars=max_scan_chars)
    if scan.blocked:
        label = {
            InjectionCheckpoint.EXTERNAL_TOOL: "external content",
            InjectionCheckpoint.AGENT_OUTPUT: "agent output",
            InjectionCheckpoint.OPERATOR_INPUT: "operator input",
        }[checkpoint]
        return (
            f"[BLOCKED: potential prompt injection in {label} — operator review required.]",
            scan,
        )
    return text, scan


def guard_operator_input(text: str, *, field: str = "input") -> str:
    """Checkpoint 1 — reject operator goals, triage prompts, and thread notes."""

    blob = (text or "").strip()
    if not blob:
        return blob
    scan = scan_untrusted_text(blob, checkpoint=InjectionCheckpoint.OPERATOR_INPUT)
    if scan.blocked:
        _logger.warning(
            "prompt_injection_guard.operator_input_blocked",
            agent_id="operator_hub",
            field=field,
            matched_pattern=scan.matched_pattern,
        )
        raise PromptInjectionViolationError(
            f"{field} blocked: potential prompt injection detected.",
        )
    return blob


def guard_agent_output(text: str) -> str:
    """Checkpoint 3 — sanitize sub-agent output before operator reports."""

    safe, scan = sanitize_untrusted_text(text, checkpoint=InjectionCheckpoint.AGENT_OUTPUT)
    if scan.blocked:
        _logger.warning(
            "prompt_injection_guard.agent_output_sanitized",
            agent_id="supervisor",
            matched_pattern=scan.matched_pattern,
        )
    return safe


__all__ = [
    "InjectionCheckpoint",
    "PromptInjectionScanResult",
    "PromptInjectionViolationError",
    "guard_agent_output",
    "guard_operator_input",
    "sanitize_untrusted_text",
    "scan_untrusted_text",
]
