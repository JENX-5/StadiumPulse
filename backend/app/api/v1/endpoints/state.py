from typing import Any

from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
from app.core.dependencies import get_state_manager
from app.db.models.user import User
from app.services.state import OperationalStateManager

router = APIRouter()


@router.get("/{venue_id}")
async def get_operational_state(
    venue_id: str,
    state_manager: OperationalStateManager = Depends(get_state_manager),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the current live operational state of a venue from the Redis hot-cache."""
    return await state_manager.get_state(venue_id)
