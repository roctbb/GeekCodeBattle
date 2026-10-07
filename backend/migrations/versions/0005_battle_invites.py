"""Invite admission and immutable task descriptions for battle reports."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_battle_invites"
down_revision = "0004_scoring_uniques"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("battles", sa.Column("invite_code", sa.String(32), nullable=True))
    op.create_unique_constraint("uq_battles_invite_code", "battles", ["invite_code"])
    op.add_column("battles", sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("matches", sa.Column("task_snapshot", sa.JSON(), nullable=True))
    op.create_table("battle_members",
        sa.Column("battle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("battles.id"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False))
    # Preserve access to existing participation and history; no public invites are invented.
    op.execute("""INSERT INTO battle_members (battle_id, user_id, joined_at)
        SELECT battle_id, user_id, MIN(joined_at) FROM (
            SELECT battle_id, user_id, enqueued_at AS joined_at FROM queue_entries
            UNION ALL
            SELECT r.battle_id, p.student_id, m.created_at
            FROM match_participants p JOIN matches m ON m.id = p.match_id JOIN rooms r ON r.id = m.room_id
        ) admissions GROUP BY battle_id, user_id""")
    op.execute("""UPDATE matches m SET task_snapshot = json_build_object(
        'id', t.id, 'title', t.title, 'statement_md', t.statement_md,
        'difficulty', t.difficulty, 'public_tests', COALESCE(t.config_json->'tests', '[]'::json))
        FROM tasks t WHERE t.id = m.task_id""")
    op.execute("UPDATE battles SET stopped_at = COALESCE(finished_at, updated_at) WHERE status IN ('stopped', 'finished')")


def downgrade():
    op.drop_table("battle_members")
    op.drop_column("matches", "task_snapshot")
    op.drop_column("battles", "stopped_at")
    op.drop_constraint("uq_battles_invite_code", "battles", type_="unique")
    op.drop_column("battles", "invite_code")
