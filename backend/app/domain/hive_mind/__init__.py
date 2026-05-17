"""Hive Mind package root — avoids eager ingest imports during namespace setup."""

from __future__ import annotations

from app.domain.hive_mind.service import HiveMindService

__all__ = ["HiveMindService"]
