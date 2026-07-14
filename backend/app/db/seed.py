"""
Development seed data.

Populates one demo venue with zones, a small user roster (one per role),
and a handful of resources — enough for the frontend foundation shell and
future agent modules to have real rows to query against without needing a
live event pipeline running first.

Usage:
    python -m app.db.seed
"""

from __future__ import annotations

import asyncio

import structlog
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.models.resource import Resource, ResourceStatus, ResourceType
from app.db.models.user import User, UserRole
from app.db.models.venue import Venue
from app.db.models.zone import Zone
from app.db.session import create_engine, create_session_factory, session_scope

logger = structlog.get_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEMO_ZONE_NAMES = [
    "North Concourse",
    "South Concourse",
    "Main Entrance",
    "Section 114",
    "VIP Suites",
]

DEMO_USERS = [
    ("admin@stadiumpulse.demo", "Ava Admin", UserRole.ADMIN),
    ("dispatcher@stadiumpulse.demo", "Dylan Dispatcher", UserRole.DISPATCHER),
    ("volunteer@stadiumpulse.demo", "Val Volunteer", UserRole.VOLUNTEER),
    ("fan@stadiumpulse.demo", "Finn Fan", UserRole.FAN),
]


async def seed() -> None:
    settings = get_settings()
    configure_logging(settings)

    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    async with session_scope(session_factory) as session:
        import uuid
        from sqlalchemy import select

        venue_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        existing = await session.execute(select(Venue).where(Venue.id == venue_id))
        if existing.scalar_one_or_none():
            logger.info("Database already seeded, skipping.")
            return

        venue = Venue(id=venue_id, name="Riverside Arena", timezone="America/New_York")
        session.add(venue)
        await session.flush()  # populate venue.id before FK references below

        zones = [Zone(venue_id=venue.id, name=name, capacity=2000) for name in DEMO_ZONE_NAMES]
        session.add_all(zones)

        default_password_hash = pwd_context.hash("demo-password-change-me")
        users = [
            User(
                venue_id=venue.id,
                email=email,
                hashed_password=default_password_hash,
                full_name=full_name,
                role=role,
            )
            for email, full_name, role in DEMO_USERS
        ]
        session.add_all(users)
        await session.flush()

        volunteer = next(u for u in users if u.role == UserRole.VOLUNTEER)
        resources = [
            Resource(
                venue_id=venue.id,
                current_zone_id=zones[0].id,
                label="Medical Station A",
                resource_type=ResourceType.MEDICAL,
                status=ResourceStatus.AVAILABLE,
            ),
            Resource(
                venue_id=venue.id,
                current_zone_id=zones[1].id,
                label="Security Team 1",
                resource_type=ResourceType.SECURITY,
                status=ResourceStatus.AVAILABLE,
            ),
            Resource(
                venue_id=venue.id,
                current_zone_id=zones[2].id,
                assigned_user_id=volunteer.id,
                label="Volunteer — Val",
                resource_type=ResourceType.VOLUNTEER,
                status=ResourceStatus.AVAILABLE,
            ),
        ]
        session.add_all(resources)

        logger.info(
            "seed_data_created",
            venue=venue.name,
            zones=len(zones),
            users=len(users),
            resources=len(resources),
        )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
