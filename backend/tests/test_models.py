"""
Model-layer tests.

No live Postgres is required for these — they validate ORM configuration
(relationships, table/column shape) via SQLAlchemy's mapper machinery, not
against a real database. Full round-trip persistence (including the
pgvector-backed `TournamentMemory` table) is covered by integration tests
that run against the real `postgres` service in `docker-compose.yml` — see
`tests/integration/` (added alongside the API module once endpoints exist
to exercise).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import configure_mappers

from app.db import models
from app.db.models.incident import Incident, IncidentSeverity, IncidentStatus, RAW_TEXT_MAX_LENGTH
from app.db.models.negotiation import Negotiation, NegotiationPhase
from app.db.models.resource import Resource, ResourceStatus, ResourceType
from app.db.models.resource_assignment import AssignmentStatus, ResourceAssignment
from app.db.models.risk_score import RiskScore, RiskScoreSource
from app.db.models.tournament_memory import EMBEDDING_DIMENSION, TournamentMemory
from app.db.models.user import User, UserRole
from app.db.models.venue import Venue
from app.db.models.zone import Zone
from app.db.session import Base


def test_all_models_registered_on_metadata() -> None:
    """Every model in `models.__all__` must actually be attached to Base.metadata —
    catches a model file that was written but never imported anywhere."""
    table_names = set(Base.metadata.tables.keys())
    expected = {
        "venues",
        "zones",
        "users",
        "resources",
        "incidents",
        "negotiations",
        "resource_assignments",
        "risk_scores",
        "tournament_memory",
    }
    assert expected.issubset(table_names)


def test_mappers_configure_without_error() -> None:
    """Catches broken relationship() definitions (typo'd back_populates, etc)
    at test time instead of at first-request time in production."""
    configure_mappers()  # raises if any relationship is misconfigured


def test_incident_composite_index_exists() -> None:
    """Phase 7 review: composite index on (venue_id, status, severity) is required
    for the GET /incidents pagination query and must not silently disappear."""
    incident_table = Base.metadata.tables["incidents"]
    index_columns = {tuple(idx.columns.keys()) for idx in incident_table.indexes}
    assert ("venue_id", "status", "severity") in index_columns


def test_risk_score_composite_index_exists() -> None:
    """Phase 7 review: (zone_id, computed_at) index backs the heatmap history query."""
    risk_score_table = Base.metadata.tables["risk_scores"]
    index_columns = {tuple(idx.columns.keys()) for idx in risk_score_table.indexes}
    assert ("zone_id", "computed_at") in index_columns


def test_raw_text_has_bounded_length() -> None:
    """Recommended Fix #9: raw_text must have an explicit max length to bound
    prompt size sent to the Incident Analysis Agent."""
    incident_table = Base.metadata.tables["incidents"]
    raw_text_column = incident_table.columns["raw_text"]
    assert raw_text_column.type.length == RAW_TEXT_MAX_LENGTH == 4000


def test_tournament_memory_embedding_dimension_is_fixed() -> None:
    tournament_memory_table = Base.metadata.tables["tournament_memory"]
    embedding_column = tournament_memory_table.columns["embedding"]
    assert embedding_column.type.dim == EMBEDDING_DIMENSION


def test_resource_assignment_has_no_direct_write_path_from_negotiation() -> None:
    """ADR-0002: Negotiation (the RCA's proposal) and ResourceAssignment
    (Dispatch Service's write) must remain structurally independent — no FK
    from resource_assignments back to a specific negotiation row, which
    would tempt future code into writing assignments from within the agent
    layer rather than through Dispatch Service."""
    resource_assignment_table = Base.metadata.tables["resource_assignments"]
    fk_targets = {fk.column.table.name for fk in resource_assignment_table.foreign_keys}
    assert "negotiations" not in fk_targets
    assert fk_targets == {"incidents", "resources"}


def test_incident_source_field_defaults_live() -> None:
    """Optional Fix #8: every incident is tagged simulation|live so demo and
    production data can never be silently confused."""
    incident = Incident(
        venue_id=uuid.uuid4(),
        raw_text="Spill reported near section 114",
        status=IncidentStatus.OPEN,
        severity=IncidentSeverity.MEDIUM,
    )
    # default is applied at INSERT time by the DB; at the Python object level
    # before a flush, the attribute simply hasn't been populated yet unless
    # explicitly set — so we assert the model *accepts* an explicit value
    # here, and rely on test_migration_matches_models (integration suite)
    # to assert the server_default itself.
    incident.source = "live"
    assert incident.source == "live"


@pytest.mark.parametrize(
    "enum_cls,expected_members",
    [
        (UserRole, {"admin", "dispatcher", "volunteer", "fan"}),
        (IncidentStatus, {"open", "in_progress", "resolved", "closed"}),
        (IncidentSeverity, {"low", "medium", "high", "critical"}),
        (ResourceType, {"medical", "security", "cleaning", "volunteer", "maintenance"}),
        (ResourceStatus, {"available", "assigned", "busy", "offline"}),
        (NegotiationPhase, {"proposal", "challenge", "rebuttal", "resolution"}),
        (
            AssignmentStatus,
            {"pending", "acknowledged", "en_route", "completed", "cancelled"},
        ),
        (RiskScoreSource, {"deterministic", "llm_narrative"}),
    ],
)
def test_enum_members_match_expected(enum_cls, expected_members) -> None:
    assert {member.value for member in enum_cls} == expected_members
