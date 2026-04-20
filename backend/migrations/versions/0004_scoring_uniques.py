"""add unique constraints for scoring idempotency

Revision ID: 0004_scoring_uniques
Revises: 0003_participant_disconnected_at
Create Date: 2026-04-20
"""
from alembic import op


revision = "0004_scoring_uniques"
down_revision = "0003_participant_disconnected_at"
branch_labels = None
depends_on = None


def upgrade():
    # Keep the earliest event/history row and remove accidental duplicates
    # before adding unique constraints.
    op.execute(
        """
        DELETE FROM score_events se
        USING (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY match_id, student_id, reason
                    ORDER BY created_at ASC, id ASC
                ) AS rn
            FROM score_events
        ) dup
        WHERE se.id = dup.id
          AND dup.rn > 1
        """
    )
    op.execute(
        """
        DELETE FROM rating_history rh
        USING (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY user_id, match_id
                    ORDER BY created_at ASC, id ASC
                ) AS rn
            FROM rating_history
        ) dup
        WHERE rh.id = dup.id
          AND dup.rn > 1
        """
    )

    op.create_unique_constraint(
        "uq_score_event_match_student_reason",
        "score_events",
        ["match_id", "student_id", "reason"],
    )
    op.create_unique_constraint(
        "uq_rating_history_user_match",
        "rating_history",
        ["user_id", "match_id"],
    )


def downgrade():
    op.drop_constraint("uq_rating_history_user_match", "rating_history", type_="unique")
    op.drop_constraint("uq_score_event_match_student_reason", "score_events", type_="unique")
