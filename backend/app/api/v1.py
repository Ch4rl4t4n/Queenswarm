"""Versioned HTTP surface — auth, breaker workflows, and swarm routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routers import agents as agents_router
from app.api.routers import auth as auth_router
from app.api.routers import dashboard_session as dashboard_session_router
from app.api.routers import dashboard as dashboard_router
from app.api.routers import operator as operator_router
from app.api.routers import jobs as jobs_router
from app.api.routers import plugins_catalog as plugins_catalog_router
from app.api.routers import learning as learning_router
from app.api.routers import realtime_ballroom as realtime_ballroom_router
from app.api.routers import recipes as recipes_router
from app.api.routers import simulations as simulations_router
from app.api.routers import swarms as swarms_router
from app.api.routers import tasks as tasks_router
from app.api.routers import workflows as workflows_router

api_v1 = APIRouter()
api_v1.include_router(auth_router.router, prefix="/auth")
api_v1.include_router(dashboard_session_router.router, prefix="/auth")
api_v1.include_router(agents_router.router, prefix="/agents")
api_v1.include_router(operator_router.router)
api_v1.include_router(dashboard_router.router)
api_v1.include_router(learning_router.router, prefix="/learning")
api_v1.include_router(workflows_router.router, prefix="/workflows")
api_v1.include_router(swarms_router.router, prefix="/swarms")
api_v1.include_router(tasks_router.router, prefix="/tasks")
api_v1.include_router(jobs_router.router, prefix="/jobs")
api_v1.include_router(simulations_router.router, prefix="/simulations")
api_v1.include_router(recipes_router.router, prefix="/recipes")
api_v1.include_router(plugins_catalog_router.router, prefix="/plugins")
api_v1.include_router(realtime_ballroom_router.get_realtime_router())
api_v1.include_router(realtime_ballroom_router.ballroom_router)

__all__ = ["api_v1"]
