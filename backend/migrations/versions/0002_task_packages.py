"""task packages

Revision ID: 0002_task_packages
Revises: 0001_initial_schema
Create Date: 2026-04-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '0002_task_packages'
down_revision = '0001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'task_packages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'task_package_tasks',
        sa.Column('package_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['package_id'], ['task_packages.id']),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id']),
        sa.PrimaryKeyConstraint('package_id', 'task_id'),
    )

    op.create_table(
        'battle_task_packages',
        sa.Column('battle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('package_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['battle_id'], ['battles.id']),
        sa.ForeignKeyConstraint(['package_id'], ['task_packages.id']),
        sa.PrimaryKeyConstraint('battle_id', 'package_id'),
    )


def downgrade():
    op.drop_table('battle_task_packages')
    op.drop_table('task_package_tasks')
    op.drop_table('task_packages')
