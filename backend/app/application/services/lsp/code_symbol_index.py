"""Lightweight repo symbol index (AST for Python, regex for TypeScript)."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from app.core.logging import get_logger

_logger = get_logger(__name__)

_SCAN_ROOTS: tuple[str, ...] = ("backend/app", "frontend")
_SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        "__pycache__",
        ".git",
        ".next",
        "node_modules",
        "venv",
        ".venv",
        "dist",
        "build",
        ".pytest_cache",
    },
)
_PY_SUFFIXES: frozenset[str] = frozenset({".py"})
_TS_SUFFIXES: frozenset[str] = frozenset({".ts", ".tsx"})

_TS_SYMBOL_RE = re.compile(
    r"^\s*export\s+(?:async\s+)?(?:function|class|interface|type|const|enum)\s+([A-Za-z_][\w$]*)",
    re.MULTILINE,
)
_TS_FN_RE = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_][\w$]*)",
    re.MULTILINE,
)
_REF_RE_TEMPLATE = r"\b{0}\b"


@dataclass(frozen=True, slots=True)
class CodeSymbol:
    """One definitional symbol occurrence in the monorepo."""

    name: str
    kind: str
    path: str
    line: int
    signature: str | None = None


def _iter_source_files(repo_root: Path) -> list[Path]:
    """Collect indexable source files under harness scan roots."""

    files: list[Path] = []
    for rel_root in _SCAN_ROOTS:
        root = repo_root / rel_root
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in _SKIP_DIR_NAMES for part in path.parts):
                continue
            if path.suffix not in _PY_SUFFIXES and path.suffix not in _TS_SUFFIXES:
                continue
            files.append(path)
    return files


def _read_bounded(path: Path, *, max_bytes: int) -> str | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if len(raw) > max_bytes:
        return None
    return raw.decode("utf-8", errors="replace")


def _python_symbols(path: Path, rel: str, source: str) -> list[CodeSymbol]:
    try:
        tree = ast.parse(source, filename=rel)
    except SyntaxError:
        return []
    out: list[CodeSymbol] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            out.append(CodeSymbol(name=node.name, kind="class", path=rel, line=node.lineno))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function"
            args = [a.arg for a in node.args.args[:6]]
            sig = f"{node.name}({', '.join(args)})" if args else f"{node.name}()"
            out.append(
                CodeSymbol(name=node.name, kind=kind, path=rel, line=node.lineno, signature=sig),
            )
    return out


def _typescript_symbols(path: Path, rel: str, source: str) -> list[CodeSymbol]:
    out: list[CodeSymbol] = []
    for match in _TS_SYMBOL_RE.finditer(source):
        name = match.group(1)
        line = source[: match.start()].count("\n") + 1
        kind = "export"
        if "class " in match.group(0):
            kind = "class"
        elif "function " in match.group(0):
            kind = "function"
        elif "interface " in match.group(0):
            kind = "interface"
        elif "type " in match.group(0):
            kind = "type"
        out.append(CodeSymbol(name=name, kind=kind, path=rel, line=line))
    return out


def symbols_in_file(
    repo_root: Path,
    *,
    rel_path: str,
    max_file_bytes: int = 512_000,
) -> list[CodeSymbol]:
    """Return definitional symbols for one repo-relative file."""

    cleaned = rel_path.strip().lstrip("/")
    path = (repo_root / cleaned).resolve()
    try:
        path.relative_to(repo_root.resolve())
    except ValueError:
        return []
    if not path.is_file():
        return []
    source = _read_bounded(path, max_bytes=max_file_bytes)
    if source is None:
        return []
    if path.suffix in _PY_SUFFIXES:
        return _python_symbols(path, cleaned, source)
    if path.suffix in _TS_SUFFIXES:
        return _typescript_symbols(path, cleaned, source)
    return []


def resolve_symbol(
    repo_root: Path,
    *,
    query: str,
    limit: int = 12,
    max_file_bytes: int = 512_000,
) -> list[CodeSymbol]:
    """Fuzzy-resolve a symbol name across the monorepo index."""

    needle = query.strip()
    if len(needle) < 2:
        return []
    cap = max(1, min(limit, 50))
    exact: list[CodeSymbol] = []
    partial: list[CodeSymbol] = []
    needle_lower = needle.lower()
    for path in _iter_source_files(repo_root):
        rel = str(path.relative_to(repo_root))
        source = _read_bounded(path, max_bytes=max_file_bytes)
        if source is None:
            continue
        symbols = (
            _python_symbols(path, rel, source)
            if path.suffix in _PY_SUFFIXES
            else _typescript_symbols(path, rel, source)
        )
        for sym in symbols:
            if sym.name == needle:
                exact.append(sym)
            elif needle_lower in sym.name.lower():
                partial.append(sym)
            if len(exact) >= cap:
                return exact[:cap]
    merged = exact + [s for s in partial if s not in exact]
    return merged[:cap]


def find_references(
    repo_root: Path,
    *,
    symbol_name: str,
    limit: int = 20,
    max_file_bytes: int = 512_000,
) -> list[dict[str, int | str]]:
    """Find word-boundary references to a symbol (best-effort, no full LSP server)."""

    name = symbol_name.strip()
    if len(name) < 2:
        return []
    pattern = re.compile(_REF_RE_TEMPLATE.format(re.escape(name)))
    cap = max(1, min(limit, 100))
    hits: list[dict[str, int | str]] = []
    for path in _iter_source_files(repo_root):
        rel = str(path.relative_to(repo_root))
        source = _read_bounded(path, max_bytes=max_file_bytes)
        if source is None:
            continue
        for line_no, line in enumerate(source.splitlines(), start=1):
            if pattern.search(line):
                hits.append({"path": rel, "line": line_no, "preview": line.strip()[:240]})
                if len(hits) >= cap:
                    return hits
    return hits


def extract_goal_identifiers(goal: str) -> list[str]:
    """Pull likely symbol tokens from a natural-language supervisor goal."""

    tokens: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"`([A-Za-z_][\w$]*)`", goal):
        name = match.group(1)
        if name not in seen:
            seen.add(name)
            tokens.append(name)
    for match in re.finditer(r"\b([A-Z][a-zA-Z0-9]{2,})\b", goal):
        name = match.group(1)
        if name not in seen:
            seen.add(name)
            tokens.append(name)
    for match in re.finditer(r"\b([a-z_][a-z0-9_]{3,})\b", goal):
        name = match.group(1)
        if name in {"with", "from", "that", "this", "when", "task", "hive", "agent"}:
            continue
        if name not in seen:
            seen.add(name)
            tokens.append(name)
    return tokens[:8]


__all__ = [
    "CodeSymbol",
    "extract_goal_identifiers",
    "find_references",
    "resolve_symbol",
    "symbols_in_file",
]
