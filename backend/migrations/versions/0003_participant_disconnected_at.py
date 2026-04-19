"""add disconnected_at for match participants

Revision ID: 0003_participant_disconnected_at
Revises: 0002_task_packages
Create Date: 2026-04-20
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_participant_disconnected_at"
down_revision = "0002_task_packages"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("match_participants", sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("match_participants", "disconnected_at")
