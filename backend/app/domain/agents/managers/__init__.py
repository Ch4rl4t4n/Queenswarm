"""Phase 0.5 manager package — six seeded Ballroom lanes + registry."""

from __future__ import annotations

from app.domain.agents.managers.content_creation_manager import ContentCreationManager
from app.domain.agents.managers.execution_operations_manager import ExecutionOperationsManager
from app.domain.agents.managers.optimization_manager import OptimizationManager
from app.domain.agents.managers.personal_life_manager import PersonalLifeManager
from app.domain.agents.managers.registry import MANAGER_REGISTRY, get_manager_template, list_manager_slugs
from app.domain.agents.managers.research_intelligence_manager import ResearchIntelligenceManager
from app.domain.agents.managers.review_quality_manager import ReviewQualityManager
from app.domain.agents.managers.spec import ManagerTemplateSpec

__all__ = [
    "MANAGER_REGISTRY",
    "ContentCreationManager",
    "ExecutionOperationsManager",
    "ManagerTemplateSpec",
    "OptimizationManager",
    "PersonalLifeManager",
    "ResearchIntelligenceManager",
    "ReviewQualityManager",
    "get_manager_template",
    "list_manager_slugs",
]
