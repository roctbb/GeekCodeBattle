"""Record explicit surrender separately from the final round result."""
from alembic import op
import sqlalchemy as sa

revision = "0007_surrender"
down_revision = "0006_code_runs"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("match_participants", sa.Column("surrendered_at", sa.DateTime(timezone=True), nullable=True))
    # Before this migration an unfinished loss was the explicit surrender marker.
    op.execute(sa.text("""
        UPDATE match_participants SET surrendered_at = CURRENT_TIMESTAMP
        WHERE result_type = 'loss' AND accepted_at IS NULL
          AND match_id IN (SELECT id FROM matches WHERE finished_at IS NULL)
    """))


def downgrade():
    op.drop_column("match_participants", "surrendered_at")
