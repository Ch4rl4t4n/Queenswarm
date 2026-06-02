"""Pre-tool denylist — block dangerous command patterns in Maintainer goals before queue."""

from __future__ import annotations

import re
from typing import Final

# Patterns blocked in Maintainer goal text (not exhaustive shell parser — fast guardrail).
_MAINTAINER_BLOCKED_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("force_push_main", re.compile(r"git\s+push\b[^;\n]*--force\b[^;\n]*\b(main|master)\b", re.I)),
    ("force_push", re.compile(r"git\s+push\b[^;\n]*--force", re.I)),
    ("deploy_prod", re.compile(r"deploy-prod\.sh|docker\s+compose\b[^;\n]*prod", re.I)),
    ("compose_down", re.compile(r"docker\s+compose\b[^;\n]*\bdown\b", re.I)),
    ("rm_rf_root", re.compile(r"rm\s+-rf\s+/(\s|$)", re.I)),
    ("drop_database", re.compile(r"drop\s+(database|schema|table)\b", re.I)),
    ("truncate_table", re.compile(r"truncate\s+table\b", re.I)),
    ("env_prod_write", re.compile(r"(^|[\s'\"])\.env\.prod\b", re.I)),
    ("secret_literal", re.compile(r"(api[_-]?key|secret[_-]?key|password)\s*=\s*['\"][^'\"]{8,}", re.I)),
    ("curl_pipe_bash", re.compile(r"curl\b[^|\n]*\|\s*(ba)?sh", re.I)),
)


def scan_maintainer_text_for_violations(text: str) -> list[str]:
    """Return ids of denylist patterns matched in free text.

    Args:
        text: Goal, plan, or operator prompt excerpt.

    Returns:
        List of pattern ids (empty when clean).
    """
    if not text.strip():
        return []
    hits: list[str] = []
    for pattern_id, compiled in _MAINTAINER_BLOCKED_PATTERNS:
        if compiled.search(text):
            hits.append(pattern_id)
    return hits


def pre_tool_denylist_summary() -> list[dict[str, str]]:
    """Human-readable denylist for harness UI and Maintainer goal footer."""

    labels = {
        "force_push_main": "No force-push to main/master",
        "force_push": "No git push --force",
        "deploy_prod": "No direct deploy-prod / prod compose",
        "compose_down": "No docker compose down",
        "rm_rf_root": "No rm -rf /",
        "drop_database": "No DROP DATABASE/TABLE",
        "truncate_table": "No TRUNCATE TABLE",
        "env_prod_write": "No .env.prod edits",
        "secret_literal": "No hardcoded secrets in goals",
        "curl_pipe_bash": "No curl | bash",
    }
    return [{"id": pid, "label": labels.get(pid, pid)} for pid, _ in _MAINTAINER_BLOCKED_PATTERNS]


__all__ = [
    "pre_tool_denylist_summary",
    "scan_maintainer_text_for_violations",
]
