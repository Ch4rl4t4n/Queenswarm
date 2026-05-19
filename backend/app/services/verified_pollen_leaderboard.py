"""Compatibility shim — canonical service: ``app.application.services.verified_pollen_leaderboard``."""

from __future__ import annotations

from app.application.services.verified_pollen_leaderboard import (
    fetch_verified_pollen_leaderboard,
    record_verified_pollen_reward,
)

__all__ = ["fetch_verified_pollen_leaderboard", "record_verified_pollen_reward"]
