"""Practice executions never participate in scoring or submission history."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_code_runs"
down_revision = "0005_battle_invites"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("code_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("match_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("language", sa.Text(), nullable=False),
        sa.Column("source_code", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("tests", sa.JSON(), nullable=False),
        sa.Column("verdict", sa.Text(), nullable=False),
        sa.Column("checker_comment_raw", sa.Text(), nullable=True),
        sa.Column("checker_status_raw", sa.Text(), nullable=True),
        sa.Column("external_run_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_code_runs_match_id", "code_runs", ["match_id"])


def downgrade():
    op.drop_table("code_runs")
