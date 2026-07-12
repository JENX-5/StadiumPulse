"""
Top-level v1 API router.

Individual domain routers (incidents, resources, risk, memory — added in
their own future modules) are included here. Keeping this as a thin
aggregator means `main.py` never needs to know about individual route
files as the API surface grows.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.incidents import router as incidents_router
from app.api.v1.endpoints.memory import router as memory_router
from app.api.v1.endpoints.resources import router as resources_router
from app.api.v1.endpoints.risk import router as risk_router
from app.api.v1.endpoints.simulation import router as simulation_router
from app.api.v1.endpoints.state import router as state_router
from app.api.v1.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(incidents_router, prefix="/incidents", tags=["Incidents"])
api_router.include_router(memory_router, prefix="/memory", tags=["Memory"])
api_router.include_router(resources_router, prefix="/resources", tags=["Resources"])
api_router.include_router(risk_router, prefix="/risk", tags=["Risk"])
api_router.include_router(simulation_router, prefix="/simulation", tags=["Simulation"])
api_router.include_router(state_router, prefix="/state", tags=["State"])
