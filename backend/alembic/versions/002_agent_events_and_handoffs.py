"""agent events and escalation handoffs

Revision ID: 002
Revises: 001
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agent_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("conversation_id", sa.String, nullable=False, index=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("event_type", sa.String, nullable=False),
        sa.Column("payload", JSONB, nullable=False, server_default="{}"),
    )
    op.create_table(
        "escalation_handoffs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("conversation_id", sa.String, nullable=False, unique=True),
        sa.Column("reason", sa.Text),
        sa.Column("customer", sa.String),
        sa.Column("orders_reviewed", JSONB),
        sa.Column("actions_attempted", JSONB),
        sa.Column("sentiment", sa.String(50)),
        sa.Column("recommended_next_step", sa.Text),
        sa.Column("raw_summary", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table("escalation_handoffs")
    op.drop_table("agent_events")