"""Scorecard metadata for letagentscook.org product badges (REV3)."""

from __future__ import annotations

import re
from pathlib import Path

_SCORECARD_LINE = re.compile(
    r"-\s+`([^`]+)`\s+—\s+(\d+)/100\s+(\w+)",
    re.IGNORECASE,
)


def _resolve_export_root(export_root: Path | None = None) -> Path:
    if export_root is not None:
        return export_root.expanduser().resolve()
    candidates = (
        Path("exports"),
        Path(__file__).resolve().parents[4] / "exports",
        Path("/exports"),
        Path("/app/exports"),
    )
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if (resolved / "GUMROAD_SCORECARD.md").is_file() or (resolved / "gumroad-ready").is_dir():
            return resolved
    return Path("exports").resolve()


def parse_scorecard_index(scorecard_md: str) -> dict[str, tuple[int, str]]:
    """Map slug → (score, verdict) from GUMROAD_SCORECARD.md."""

    index: dict[str, tuple[int, str]] = {}
    for match in _SCORECARD_LINE.finditer(scorecard_md):
        slug = match.group(1).strip().lower()
        index[slug] = (int(match.group(2)), str(match.group(3)).lower())
    return index


def load_scorecard_index(export_root: Path | None = None) -> dict[str, tuple[int, str]]:
    """Load scorecard index from exports root."""

    root = _resolve_export_root(export_root)
    path = root / "GUMROAD_SCORECARD.md"
    if not path.is_file():
        return {}
    try:
        return parse_scorecard_index(path.read_text(encoding="utf-8"))
    except OSError:
        return {}


def is_scorecard_clean(*, score: int, verdict: str) -> bool:
    """Return True when listing meets REV3 badge gate."""

    return score >= 100 and verdict in {"ready", "uploaded"}


def scorecard_fields_for_slug(
    slug: str,
    *,
    manifest_score: int,
    export_root: Path | None = None,
    index: dict[str, tuple[int, str]] | None = None,
) -> tuple[int, str, bool]:
    """Return (score, verdict, scorecard_clean) for one catalog slug."""

    lookup = index if index is not None else load_scorecard_index(export_root)
    row = lookup.get(slug.strip().lower())
    if row is None:
        score = manifest_score
        verdict = "ready" if score >= 100 else "review"
        return score, verdict, is_scorecard_clean(score=score, verdict=verdict)
    score, verdict = row
    return score, verdict, is_scorecard_clean(score=score, verdict=verdict)


__all__ = [
    "is_scorecard_clean",
    "load_scorecard_index",
    "parse_scorecard_index",
    "scorecard_fields_for_slug",
]
