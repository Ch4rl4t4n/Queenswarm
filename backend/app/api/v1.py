"""Versioned HTTP surface — auth, breaker workflows, and swarm routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routers import auth as auth_router
from app.api.routers import jobs as jobs_router
from app.api.routers import recipes as recipes_router
from app.api.routers import simulations as simulations_router
from app.api.routers import swarms as swarms_router
from app.api.routers import tasks as tasks_router
from app.api.routers import workflows as workflows_router

api_v1 = APIRouter()
api_v1.include_router(auth_router.router, prefix="/auth")
api_v1.include_router(workflows_router.router, prefix="/workflows")
api_v1.include_router(swarms_router.router, prefix="/swarms")
api_v1.include_router(tasks_router.router, prefix="/tasks")
api_v1.include_router(jobs_router.router, prefix="/jobs")
api_v1.include_router(simulations_router.router, prefix="/simulations")
api_v1.include_router(recipes_router.router, prefix="/recipes")

__all__ = ["api_v1"]
