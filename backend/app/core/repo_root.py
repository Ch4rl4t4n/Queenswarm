"""Monorepo root resolution for harness and skill reference loaders."""

from __future__ import annotations

from pathlib import Path


def resolve_repo_root() -> Path:
    """Return Queenswarm monorepo root (parent of ``backend/``)."""

    return Path(__file__).resolve().parents[2]


__all__ = ["resolve_repo_root"]
