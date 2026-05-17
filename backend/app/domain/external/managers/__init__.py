"""Specialised routing façades for external integration lanes."""

from __future__ import annotations

from app.domain.external.managers.food_ordering_manager import FoodOrderingManager
from app.domain.external.managers.generic_project_manager import GenericProjectManager
from app.domain.external.managers.trading_manager import TradingManager

__all__ = ["FoodOrderingManager", "GenericProjectManager", "TradingManager"]
