from fastapi import APIRouter, Depends

from app.api.auth import RequireRole, get_current_user
from app.core.dependencies import get_simulation_engine
from app.db.models.user import User, UserRole
from app.schemas.simulation import SimulationControl, SimulationStatusResponse
from app.services.simulation import SimulationEngine

router = APIRouter()


@router.post("/control", response_model=SimulationStatusResponse)
async def control_simulation(
    control: SimulationControl,
    engine: SimulationEngine = Depends(get_simulation_engine),
    current_user: User = Depends(RequireRole(UserRole.DISPATCHER)),
):
    """Control the Simulation Engine (start, stop, pause, resume).

    Dispatcher-gated: this controls the shared live demo/venue state for
    every connected client, so an unauthenticated caller must not be able
    to start, stop, or pause it out from under legitimate operators.
    """
    return engine.apply_control(control)


@router.get("/status", response_model=SimulationStatusResponse)
async def get_simulation_status(
    engine: SimulationEngine = Depends(get_simulation_engine),
    current_user: User = Depends(get_current_user),
):
    """Get the current status of the Simulation Engine."""
    return engine.get_status()
