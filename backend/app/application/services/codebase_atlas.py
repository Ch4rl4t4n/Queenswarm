"""Codebase Atlas — LOC, git effort estimate, and FE/BE architecture map for Command Center."""

from __future__ import annotations

import asyncio
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import structlog

from app.application.services.queen_maintainer.tech_health import (
    _resolve_backend_root,
    _resolve_frontend_root,
    resolve_repo_root,
)
from app.core.config import settings
from app.core.redis_client import get_json, set_json

logger = structlog.get_logger(__name__)

CODEBASE_ATLAS_CACHE_KEY = "queenswarm:codebase_atlas:v1"
CODEBASE_ATLAS_CACHE_TTL_SEC = 600

LayerKind = Literal["frontend", "backend"]

_SKIP_FILE_NAMES = frozenset(
    {
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "poetry.lock",
        "uv.lock",
    }
)

_SKIP_EXTENSIONS_EXTRA = frozenset({".map", ".lock"})

_SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".next",
        ".turbo",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        "dist",
        "build",
        "coverage",
        "htmlcov",
        ".cursor",
        "mcps",
        ".playwright",
    }
)

_COUNTABLE_EXTENSIONS: dict[str, str] = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TSX",
    ".js": "JavaScript",
    ".jsx": "JSX",
    ".css": "CSS",
    ".md": "Markdown",
    ".sh": "Shell",
    ".sql": "SQL",
    ".yml": "YAML",
    ".yaml": "YAML",
}

# Architecture layers — paths relative to repo root.
_FE_LAYERS: tuple[tuple[str, str, str], ...] = (
    ("app", "App Router · pages", "Routes, layouts, server components"),
    ("components/hive", "Hive components", "Dashboard, swarms, hive-mind UI"),
    ("components/ui", "UI kit · V4", "Cards, badges, design system"),
    ("lib", "Shared lib", "API client, types, hooks"),
    ("e2e", "E2E · Playwright", "Production walkthrough specs"),
)

_BE_LAYERS: tuple[tuple[str, str, str], ...] = (
    ("backend/app/presentation", "Presentation · API", "FastAPI routers, WebSocket"),
    ("backend/app/application", "Application services", "Orchestration, business logic"),
    ("backend/app/domain", "Domain", "Agents, hive-mind, outputs"),
    ("backend/app/infrastructure", "Infrastructure", "SQLAlchemy, persistence"),
    ("backend/app/worker", "Workers · Celery", "Beat schedule, background tasks"),
    ("backend/app/agents", "Agent runtime", "Executor, tool registry"),
    ("backend/app/core", "Core", "Config, LLM router, database"),
    ("backend/tests", "Tests · pytest", "Unit + integration"),
)

_LAYER_COLORS: dict[str, str] = {
    "App Router · pages": "#6fd6ff",
    "Hive components": "#e879f9",
    "UI kit · V4": "#9966ff",
    "Shared lib": "#5be3b2",
    "E2E · Playwright": "#ffb800",
    "Presentation · API": "#6fd6ff",
    "Application services": "#e879f9",
    "Domain": "#5be3b2",
    "Infrastructure": "#ffb800",
    "Workers · Celery": "#9966ff",
    "Agent runtime": "#ff00aa",
    "Core": "#ffb800",
    "Tests · pytest": "#5be3b2",
}


@dataclass(frozen=True, slots=True)
class _FileStat:
    lines: int
    language: str


def _should_skip_file(path: Path) -> bool:
    if path.name in _SKIP_FILE_NAMES:
        return True
    if path.suffix.lower() in _SKIP_EXTENSIONS_EXTRA:
        return True
    return False


def _should_skip_dir(name: str) -> bool:
    return name in _SKIP_DIR_NAMES or name.startswith(".")


def _count_file_lines(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return 0
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _walk_loc(root: Path, *, rel_prefix: str = "") -> dict[str, Any]:
    """Count lines under *root* grouped by extension language."""

    by_language: dict[str, int] = defaultdict(int)
    by_ext: dict[str, int] = defaultdict(int)
    total_lines = 0
    total_files = 0

    if not root.is_dir():
        return {
            "root": str(root),
            "available": False,
            "total_lines": 0,
            "total_files": 0,
            "by_language": {},
            "by_extension": {},
        }

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(_should_skip_dir(part) for part in path.parts):
            continue
        if _should_skip_file(path):
            continue
        ext = path.suffix.lower()
        if ext not in _COUNTABLE_EXTENSIONS:
            continue
        lines = _count_file_lines(path)
        lang = _COUNTABLE_EXTENSIONS[ext]
        by_language[lang] += lines
        by_ext[ext] += lines
        total_lines += lines
        total_files += 1

    return {
        "root": str(root),
        "available": True,
        "total_lines": total_lines,
        "total_files": total_files,
        "by_language": dict(sorted(by_language.items(), key=lambda kv: -kv[1])),
        "by_extension": dict(sorted(by_ext.items(), key=lambda kv: -kv[1])),
    }


def _layer_loc(repo: Path, rel_path: str) -> dict[str, Any]:
    """LOC for one architecture layer folder."""

    target = repo / rel_path
    lines = 0
    files = 0
    if target.is_dir():
        for path in target.rglob("*"):
            if not path.is_file():
                continue
            if any(_should_skip_dir(part) for part in path.relative_to(target).parts):
                continue
            if _should_skip_file(path):
                continue
            ext = path.suffix.lower()
            if ext not in _COUNTABLE_EXTENSIONS:
                continue
            lines += _count_file_lines(path)
            files += 1
    return {"lines": lines, "files": files, "path": rel_path, "exists": target.is_dir()}


def _build_architecture_layers(
    repo: Path,
    spec: tuple[tuple[str, str, str], ...],
    kind: LayerKind,
) -> list[dict[str, Any]]:
    """Build ordered architecture layer nodes with LOC."""

    layers: list[dict[str, Any]] = []
    for idx, (rel, label, desc) in enumerate(spec):
        stats = _layer_loc(repo, rel)
        layers.append(
            {
                "id": f"{kind}-{idx}",
                "label": label,
                "description": desc,
                "path": rel,
                "lines": stats["lines"],
                "files": stats["files"],
                "exists": stats["exists"],
                "color": _LAYER_COLORS.get(label, "#6fd6ff"),
                "order": idx,
            }
        )
    return layers


def _git_commit_timestamps(repo: Path) -> list[datetime]:
    """Return all commit author timestamps (UTC) from git log."""

    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "log", "--format=%aI", "--reverse"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("codebase_atlas.git_log_failed", error=str(exc))
        return []

    if proc.returncode != 0 or not proc.stdout.strip():
        return []

    out: list[datetime] = []
    for line in proc.stdout.splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            out.append(ts.astimezone(UTC))
        except ValueError:
            continue
    return out


def _estimate_dev_hours(timestamps: list[datetime], *, session_gap_hours: float = 2.0) -> dict[str, Any]:
    """Estimate active dev hours via commit session clustering."""

    if not timestamps:
        return {
            "estimated_hours": 0.0,
            "active_days": 0,
            "commit_count": 0,
            "first_commit_at": None,
            "last_commit_at": None,
            "sessions": 0,
        }

    gap = timedelta(hours=session_gap_hours)
    sessions: list[tuple[datetime, datetime, int]] = []
    session_start = timestamps[0]
    session_end = timestamps[0]
    session_commits = 1

    for ts in timestamps[1:]:
        if ts - session_end > gap:
            sessions.append((session_start, session_end, session_commits))
            session_start = ts
            session_end = ts
            session_commits = 1
        else:
            session_end = ts
            session_commits += 1
    sessions.append((session_start, session_end, session_commits))

    total_hours = 0.0
    for start, end, count in sessions:
        span_h = max(0.0, (end - start).total_seconds() / 3600.0)
        # Base 20 min per session + span, cap 6h per session; floor from commit count.
        session_h = min(6.0, max(0.33 * count, 0.33 + span_h))
        total_hours += session_h

    active_days = len({ts.date() for ts in timestamps})

    return {
        "estimated_hours": round(total_hours, 1),
        "active_days": active_days,
        "commit_count": len(timestamps),
        "first_commit_at": timestamps[0].isoformat(),
        "last_commit_at": timestamps[-1].isoformat(),
        "sessions": len(sessions),
    }


def _git_weekly_activity(repo: Path, *, weeks: int = 12) -> list[dict[str, Any]]:
    """Commits per ISO week for trend chart."""

    timestamps = _git_commit_timestamps(repo)
    if not timestamps:
        return []

    cutoff = datetime.now(tz=UTC) - timedelta(weeks=weeks)
    buckets: dict[str, int] = defaultdict(int)
    for ts in timestamps:
        if ts < cutoff:
            continue
        iso = ts.isocalendar()
        key = f"{iso.year}-W{iso.week:02d}"
        buckets[key] += 1

    return [{"week": k, "commits": v} for k, v in sorted(buckets.items())]


def build_codebase_atlas(*, repo_root: Path | None = None) -> dict[str, Any]:
    """Build full Codebase Atlas payload for Command Center."""

    configured = (settings.codebase_atlas_repo_root or "").strip()
    if repo_root is None and configured:
        repo = Path(configured)
    else:
        repo = repo_root or resolve_repo_root()
    backend = _resolve_backend_root(repo)
    frontend = _resolve_frontend_root(repo)

    fe_loc = _walk_loc(frontend) if frontend.is_dir() else {"available": False, "total_lines": 0, "total_files": 0, "by_language": {}}
    be_loc = _walk_loc(backend)
    docs_loc = _walk_loc(repo / "docs") if (repo / "docs").is_dir() else {"available": False, "total_lines": 0, "total_files": 0, "by_language": {}}
    scripts_loc = _walk_loc(repo / "scripts") if (repo / "scripts").is_dir() else {"available": False, "total_lines": 0, "total_files": 0, "by_language": {}}

    fe_lines = int(fe_loc.get("total_lines") or 0)
    be_lines = int(be_loc.get("total_lines") or 0)
    docs_lines = int(docs_loc.get("total_lines") or 0)
    scripts_lines = int(scripts_loc.get("total_lines") or 0)
    total_lines = fe_lines + be_lines + docs_lines + scripts_lines

    git_repo = repo if (repo / ".git").is_dir() else None
    timestamps = _git_commit_timestamps(git_repo) if git_repo else []
    git_stats = _estimate_dev_hours(timestamps)
    weekly = _git_weekly_activity(git_repo) if git_repo else []

    fe_layers = _build_architecture_layers(repo, _FE_LAYERS, "frontend")
    be_layers = _build_architecture_layers(repo, _BE_LAYERS, "backend")

    # Merged language chart data
    lang_totals: dict[str, int] = defaultdict(int)
    for block in (fe_loc, be_loc, docs_loc, scripts_loc):
        for lang, count in (block.get("by_language") or {}).items():
            lang_totals[lang] += int(count)

    stack_split = [
        {"name": "Frontend", "lines": fe_lines, "color": "#6fd6ff"},
        {"name": "Backend", "lines": be_lines, "color": "#e879f9"},
        {"name": "Docs", "lines": docs_lines, "color": "#ffb800"},
        {"name": "Scripts", "lines": scripts_lines, "color": "#5be3b2"},
    ]

    return {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "repo_root": str(repo),
        "git_available": git_repo is not None,
        "summary": {
            "total_lines": total_lines,
            "frontend_lines": fe_lines,
            "backend_lines": be_lines,
            "frontend_files": int(fe_loc.get("total_files") or 0),
            "backend_files": int(be_loc.get("total_files") or 0),
            "estimated_dev_hours": git_stats["estimated_hours"],
            "commit_count": git_stats["commit_count"],
            "active_dev_days": git_stats["active_days"],
            "coding_sessions": git_stats["sessions"],
            "first_commit_at": git_stats["first_commit_at"],
            "last_commit_at": git_stats["last_commit_at"],
        },
        "stack_split": [row for row in stack_split if row["lines"] > 0],
        "languages": [
            {"language": lang, "lines": count, "pct": round(count / total_lines * 100, 1) if total_lines else 0}
            for lang, count in sorted(lang_totals.items(), key=lambda kv: -kv[1])
        ],
        "weekly_commits": weekly,
        "frontend": {
            "loc": fe_loc,
            "architecture": {
                "kind": "frontend",
                "title": "Frontend · Next.js 15",
                "flow": ["App Router", "Hive UI", "UI kit", "lib/api"],
                "layers": fe_layers,
            },
        },
        "backend": {
            "loc": be_loc,
            "architecture": {
                "kind": "backend",
                "title": "Backend · FastAPI + Celery",
                "flow": ["API routers", "Services", "Domain", "Infrastructure", "Workers"],
                "layers": be_layers,
            },
        },
    }


async def build_codebase_atlas_cached(*, repo_root: Path | None = None) -> dict[str, Any]:
    """Return atlas payload from Redis cache or a thread-pool scan (10 min TTL)."""

    cached = await get_json(CODEBASE_ATLAS_CACHE_KEY)
    if isinstance(cached, dict) and cached.get("generated_at"):
        return {**cached, "cached": True}

    payload = await asyncio.to_thread(build_codebase_atlas, repo_root=repo_root)
    await set_json(CODEBASE_ATLAS_CACHE_KEY, payload, ttl=CODEBASE_ATLAS_CACHE_TTL_SEC)
    return {**payload, "cached": False}


__all__ = ["CODEBASE_ATLAS_CACHE_KEY", "build_codebase_atlas", "build_codebase_atlas_cached"]
