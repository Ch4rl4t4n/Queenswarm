"""Versioned HTTP surface — auth, swarms/workflows/recipes/jobs plus operator essentials."""

from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.presentation.api.routers import agents as agents_router
from app.presentation.api.routers import agent_sessions as agent_sessions_router
from app.presentation.api.routers import auth as auth_router
from app.presentation.api.routers import connectors as connectors_router
from app.presentation.api.routers import connectors_dynamic as connectors_dynamic_router
from app.presentation.api.routers import dashboard as dashboard_router
from app.presentation.api.routers import dashboard_session as dashboard_session_router
from app.presentation.api.routers import external as external_router
from app.presentation.api.routers import jobs as jobs_router
from app.presentation.api.routers import learning as learning_router
from app.presentation.api.routers import marketing as marketing_router
from app.presentation.api.routers import operator as operator_router
from app.presentation.api.routers import operator_monitoring as operator_monitoring_router
from app.presentation.api.routers import plugins_catalog as plugins_catalog_router
from app.presentation.api.routers import realtime_ballroom as realtime_ballroom_router
from app.presentation.api.routers import realtime_supervisor_audit as realtime_supervisor_audit_router
from app.presentation.api.routers import recipes as recipes_router
from app.presentation.api.routers import skill_marketplace_ugc as skill_marketplace_ugc_router
from app.presentation.api.routers import simulations as simulations_router
from app.presentation.api.routers import swarms as swarms_router
from app.presentation.api.routers import system_status as system_status_router
from app.presentation.api.routers import tasks as tasks_router
from app.presentation.api.routers import workflows as workflows_router
from app.presentation.api.routers import operator_external_apis as operator_external_apis_router
from app.presentation.api.routers import operator_llm_keys as operator_llm_keys_router
from app.presentation.api.routers import operator_notifications as operator_notifications_router
from app.presentation.api.routers import hive_mind as hive_mind_router
from app.presentation.api.routers import outputs as outputs_router
from app.presentation.api.routers import oauth_consent as oauth_consent_router
from app.presentation.api.routers import settings_team as settings_team_router
from app.presentation.api.routers import settings_enterprise as settings_enterprise_router
from app.presentation.api.routers import billing as billing_router
from app.presentation.api.routers import shares as shares_router
from app.presentation.api.routers import external_api as external_api_router
from app.presentation.api.routers import tools_marketplace as tools_marketplace_router
from app.presentation.api.routers import dreaming as dreaming_router
from app.presentation.api.routers import curated_memory as curated_memory_router
from app.presentation.api.routers import goals as goals_router
from app.presentation.api.routers import agent_templates as agent_templates_router
from app.presentation.api.routers import foragers as foragers_router
from app.presentation.api.routers import paper_trading as paper_trading_router
from app.presentation.api.routers import command_center_admin as command_center_admin_router
from app.presentation.api.routers import admin_accounts as admin_accounts_router
from app.presentation.api.routers import platform_features_admin as platform_features_admin_router
from app.core.config import settings

api_v1 = APIRouter()


@api_v1.get("/health", tags=["Health"], summary="Liveness under /api/v1 (edge proxies)")
async def api_v1_health() -> dict[str, str]:
    """Cheap heartbeat mirrored for operators probing ``/api/v1/health`` through Nginx."""

    return {
        "status": "healthy",
        "service": "queenswarm-api",
        "version": __version__,
        "domain": settings.domain,
    }


api_v1.include_router(auth_router.router, prefix="/auth")
api_v1.include_router(dashboard_session_router.router, prefix="/auth")
api_v1.include_router(connectors_router.router, prefix="/connectors")
api_v1.include_router(tools_marketplace_router.router)
api_v1.include_router(oauth_consent_router.router)
api_v1.include_router(connectors_dynamic_router.router)
api_v1.include_router(agent_sessions_router.router, prefix="/agents")
api_v1.include_router(realtime_supervisor_audit_router.router, prefix="/agents")
api_v1.include_router(agents_router.router, prefix="/agents")
api_v1.include_router(operator_router.router)
api_v1.include_router(operator_monitoring_router.router)
api_v1.include_router(system_status_router.router)
api_v1.include_router(dashboard_router.router)
api_v1.include_router(settings_team_router.router)
api_v1.include_router(settings_enterprise_router.router)
api_v1.include_router(billing_router.router)
api_v1.include_router(shares_router.router)
api_v1.include_router(shares_router.public_router)
api_v1.include_router(marketing_router.public_router)
api_v1.include_router(marketing_router.router)
api_v1.include_router(external_api_router.router)
api_v1.include_router(learning_router.router, prefix="/learning")
api_v1.include_router(workflows_router.router, prefix="/workflows")
api_v1.include_router(swarms_router.router, prefix="/swarms")
api_v1.include_router(tasks_router.router, prefix="/tasks")
api_v1.include_router(jobs_router.router, prefix="/jobs")
api_v1.include_router(simulations_router.router, prefix="/simulations")
api_v1.include_router(recipes_router.router, prefix="/recipes")
api_v1.include_router(skill_marketplace_ugc_router.router, prefix="/recipes")
api_v1.include_router(plugins_catalog_router.router, prefix="/plugins")
api_v1.include_router(dreaming_router.router)
api_v1.include_router(curated_memory_router.router)
api_v1.include_router(goals_router.router)
api_v1.include_router(agent_templates_router.router)
api_v1.include_router(foragers_router.router)
api_v1.include_router(platform_features_admin_router.router)
api_v1.include_router(admin_accounts_router.router)
api_v1.include_router(command_center_admin_router.router)
api_v1.include_router(paper_trading_router.router)
api_v1.include_router(outputs_router.router)
api_v1.include_router(hive_mind_router.router)
api_v1.include_router(external_router.router)
api_v1.include_router(operator_llm_keys_router.router)
api_v1.include_router(operator_notifications_router.router)
api_v1.include_router(operator_external_apis_router.router)
api_v1.include_router(realtime_ballroom_router.get_realtime_router())
api_v1.include_router(realtime_ballroom_router.ballroom_router)

__all__ = ["api_v1", "api_v1_health"]
