"""LN2 — Anti-cheat: block critic pass when output weakens tests or guardrails."""

from __future__ import annotations

import re
from typing import Final

# loop_anti_cheat — extend Maintainer denylist heuristics to critic/AFK outputs.
_LN2_WEAKENING_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("delete_test_file", re.compile(r"\b(delete|remove|drop)\b[^.\n]{0,40}\btest(s)?\b", re.I)),
    ("skip_test_run", re.compile(r"\b(skip(ping)?|disable(d)?|no)\b[^.\n]{0,30}\b(test(s)?|pytest)\b", re.I)),
    ("lower_coverage_gate", re.compile(r"(coverage|cov-fail-under|--cov)[^.\n]{0,40}(lower|reduce|0\.|skip)", re.I)),
    ("weaken_guardrail", re.compile(r"\b(raise|increase)\b[^.\n]{0,30}\b(max_turns|cost_cap|min_score)\b", re.I)),
    ("remove_assert", re.compile(r"\b(remove|delete|comment out)\b[^.\n]{0,30}\bassert(ion)?s?\b", re.I)),
    ("no_verify_bypass", re.compile(r"\b(bypass|ignore|disable)\b[^.\n]{0,30}\b(verify|guardrail|critic)\b", re.I)),
)


def scan_output_for_anti_cheat_violations(text: str) -> list[str]:
    """Return matched anti-cheat pattern ids (empty when clean)."""

    if not str(text or "").strip():
        return []
    hits: list[str] = []
    for pattern_id, compiled in _LN2_WEAKENING_PATTERNS:
        if compiled.search(text):
            hits.append(pattern_id)
    return hits


def loop_anti_cheat_blocks_critic_pass(*, output_text: str) -> bool:
    """True when critic/operator output tries to cheat quality gates (LN2)."""

    return bool(scan_output_for_anti_cheat_violations(output_text))


__all__ = [
    "loop_anti_cheat_blocks_critic_pass",
    "scan_output_for_anti_cheat_violations",
]
