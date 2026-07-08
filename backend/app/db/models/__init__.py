"""
Import every ORM model here so `Base.metadata` is fully populated and
Alembic's autogenerate (and `configure_mappers()` in tests) can see the
complete schema from a single import: `from app.db import models`.
"""

from app.db.models.incident import Incident
from app.db.models.negotiation import Negotiation
from app.db.models.resource import Resource
from app.db.models.resource_assignment import ResourceAssignment
from app.db.models.risk_score import RiskScore
from app.db.models.tournament_memory import TournamentMemory
from app.db.models.user import User
from app.db.models.venue import Venue
from app.db.models.zone import Zone

__all__ = [
    "Incident",
    "Negotiation",
    "Resource",
    "ResourceAssignment",
    "RiskScore",
    "TournamentMemory",
    "User",
    "Venue",
    "Zone",
]
