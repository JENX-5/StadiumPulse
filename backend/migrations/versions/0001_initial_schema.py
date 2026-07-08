"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-08

Creates every table defined in `app/db/models/`, in FK-dependency order:
venues -> users, zones -> resources, incidents -> negotiations,
resource_assignments -> risk_scores -> tournament_memory.

Enables the `vector` extension (pgvector) before creating
`tournament_memory`, whose `embedding` column depends on it.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

EMBEDDING_DIMENSION = 1024


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- venues --------------------------------------------------------------
    op.create_table(
        "venues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- users -----------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "venue_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("venues.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "dispatcher", "volunteer", "fan", name="user_role"),
            nullable=False,
            server_default="fan",
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- zones -------------------------------------------------------------------
    op.create_table(
        "zones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "venue_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("venues.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("capacity", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- resources -----------------------------------------------------------
    op.create_table(
        "resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "venue_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("venues.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "current_zone_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("zones.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "assigned_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            unique=True,
        ),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column(
            "resource_type",
            sa.Enum("medical", "security", "cleaning", "volunteer", "maintenance", name="resource_type"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("available", "assigned", "busy", "offline", name="resource_status"),
            nullable=False,
            server_default="available",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # This is the exact filter the SQL pre-filter step (Critical Fix #2) uses
    # before the Resource Coordination Agent ever sees a shortlist.
    op.create_index(
        "ix_resources_venue_status_type", "resources", ["venue_id", "status", "resource_type"]
    )

    # --- incidents ---------------------------------------------------------------
    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "venue_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("venues.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "zone_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("zones.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "reported_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("raw_text", sa.String(4000), nullable=False),
        sa.Column("language", sa.String(16), nullable=True),
        sa.Column("structured_summary", postgresql.JSONB, nullable=True),
        sa.Column(
            "status",
            sa.Enum("open", "in_progress", "resolved", "closed", name="incident_status"),
            nullable=False,
            server_default="open",
        ),
        sa.Column(
            "severity",
            sa.Enum("low", "medium", "high", "critical", name="incident_severity"),
            nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "source",
            sa.Enum("simulation", "live", name="incident_source"),
            nullable=False,
            server_default="live",
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_incidents_venue_status_severity", "incidents", ["venue_id", "status", "severity"]
    )

    # --- negotiations ------------------------------------------------------------
    op.create_table(
        "negotiations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "phase",
            sa.Enum("proposal", "challenge", "rebuttal", "resolution", name="negotiation_phase"),
            nullable=False,
        ),
        sa.Column("turn_number", sa.Integer, nullable=False),
        sa.Column("agent_name", sa.String, nullable=False),
        sa.Column("content", postgresql.JSONB, nullable=False),
        sa.Column("rationale", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_negotiations_incident_turn", "negotiations", ["incident_id", "turn_number"])

    # --- resource_assignments ------------------------------------------------
    op.create_table(
        "resource_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "resource_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "acknowledged", "en_route", "completed", "cancelled",
                name="assignment_status",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("assigned_by", sa.String(200), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_resource_assignments_incident", "resource_assignments", ["incident_id"]
    )
    op.create_index(
        "ix_resource_assignments_resource", "resource_assignments", ["resource_id"]
    )

    # --- risk_scores ---------------------------------------------------------
    op.create_table(
        "risk_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "zone_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("zones.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "source",
            sa.Enum("deterministic", "llm_narrative", name="risk_score_source"),
            nullable=False,
        ),
        sa.Column("contributing_factors", postgresql.JSONB, nullable=True),
        sa.Column("narrative", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_risk_scores_zone_computed_at", "risk_scores", ["zone_id", "computed_at"])

    # --- tournament_memory (requires pgvector extension, enabled above) --------
    op.create_table(
        "tournament_memory",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "venue_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("venues.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("summary", sa.String, nullable=False),
        sa.Column("pattern_type", sa.String, nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSION), nullable=False),
        sa.Column(
            "source_incident_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_tournament_memory_embedding",
        "tournament_memory",
        ["embedding"],
        postgresql_using="ivfflat",
        postgresql_with={"lists": "100"},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_table("tournament_memory")
    op.drop_table("risk_scores")
    op.drop_table("resource_assignments")
    op.drop_table("negotiations")
    op.drop_table("incidents")
    op.drop_table("resources")
    op.drop_table("zones")
    op.drop_table("users")
    op.drop_table("venues")

    # Drop enum types explicitly — Postgres does not drop them automatically
    # when the owning column/table is dropped.
    for enum_name in (
        "risk_score_source",
        "assignment_status",
        "negotiation_phase",
        "incident_source",
        "incident_severity",
        "incident_status",
        "resource_status",
        "resource_type",
        "user_role",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")

    op.execute("DROP EXTENSION IF EXISTS vector")
