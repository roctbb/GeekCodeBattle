"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('external_id', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('season_points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('win_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('loss_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_opponents_json', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id'),
    )

    op.create_table(
        'battles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('room_size', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('statement_md', sa.Text(), nullable=False),
        sa.Column('difficulty', sa.Text(), nullable=False),
        sa.Column('check_type', sa.Text(), nullable=False),
        sa.Column('config_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'battle_tasks',
        sa.Column('battle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['battle_id'], ['battles.id']),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id']),
        sa.PrimaryKeyConstraint('battle_id', 'task_id'),
    )

    op.create_table(
        'queue_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('battle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_ready', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('enqueued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_opponents_json', sa.JSON(), nullable=False, server_default='[]'),
        sa.ForeignKeyConstraint(['battle_id'], ['battles.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('battle_id', 'user_id', name='uq_queue_battle_user'),
    )

    op.create_table(
        'rooms',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('battle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['battle_id'], ['battles.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'matches',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('room_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('finished_by', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['room_id'], ['rooms.id']),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'match_participants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('match_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('result_type', sa.Text(), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('progress', sa.Numeric(5, 4), nullable=True),
        sa.Column('place', sa.Integer(), nullable=True),
        sa.Column('is_disconnected', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint("result_type in ('win','draw','loss','no_result') or result_type is null", name='ck_result_type'),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id']),
        sa.ForeignKeyConstraint(['student_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('match_id', 'student_id', name='uq_match_student'),
    )

    op.create_table(
        'submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('match_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('language', sa.Text(), nullable=False),
        sa.Column('source_code', sa.Text(), nullable=False),
        sa.Column('verdict', sa.Text(), nullable=False, server_default='queued'),
        sa.Column('progress_value', sa.Numeric(5, 4), nullable=False, server_default='0'),
        sa.Column('visible_tests_passed', sa.Integer(), nullable=True),
        sa.Column('visible_tests_total', sa.Integer(), nullable=True),
        sa.Column('hidden_tests_passed', sa.Integer(), nullable=True),
        sa.Column('hidden_tests_total', sa.Integer(), nullable=True),
        sa.Column('external_run_id', sa.Text(), nullable=True),
        sa.Column('callback_received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('checker_status_raw', sa.Text(), nullable=True),
        sa.Column('checker_comment_raw', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id']),
        sa.ForeignKeyConstraint(['student_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'score_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('match_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('points_delta', sa.Integer(), nullable=False),
        sa.Column('rating_delta', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id']),
        sa.ForeignKeyConstraint(['student_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'rating_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('match_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('old_rating', sa.Integer(), nullable=False),
        sa.Column('new_rating', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', sa.Text(), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('payload_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('audit_log')
    op.drop_table('rating_history')
    op.drop_table('score_events')
    op.drop_table('submissions')
    op.drop_table('match_participants')
    op.drop_table('matches')
    op.drop_table('rooms')
    op.drop_table('queue_entries')
    op.drop_table('battle_tasks')
    op.drop_table('tasks')
    op.drop_table('battles')
    op.drop_table('users')
