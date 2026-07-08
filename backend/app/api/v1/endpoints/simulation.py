from fastapi import APIRouter, Depends

from app.core.dependencies import get_simulation_engine
from app.schemas.simulation import SimulationControl, SimulationStatusResponse
from app.services.simulation import SimulationEngine

router = APIRouter()


@router.post("/control", response_model=SimulationStatusResponse)
async def control_simulation(
    control: SimulationControl,
    engine: SimulationEngine = Depends(get_simulation_engine),
):
    """Control the Simulation Engine (start, stop, pause, resume)."""
    return engine.apply_control(control)


@router.get("/status", response_model=SimulationStatusResponse)
async def get_simulation_status(
    engine: SimulationEngine = Depends(get_simulation_engine),
):
    """Get the current status of the Simulation Engine."""
    return engine.get_status()
