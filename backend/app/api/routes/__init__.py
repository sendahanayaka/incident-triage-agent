"""Routes package exports."""

from fastapi import APIRouter

from backend.app.api.routes import (
    approvals,
    deployments,
    health,
    incidents,
    investigations,
    logs,
    services,
    traces,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(investigations.router)
api_router.include_router(services.router)
api_router.include_router(logs.router)
api_router.include_router(deployments.router)
api_router.include_router(incidents.router)
api_router.include_router(approvals.router)
api_router.include_router(traces.router)

__all__ = ["api_router"]
