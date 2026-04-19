from sqlalchemy.dialects.postgresql import UUID

from ..extensions import db
from .base import UUIDPKMixin, utcnow


class Task(UUIDPKMixin, db.Model):
    __tablename__ = "tasks"

    title = db.Column(db.Text, nullable=False)
    statement_md = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.Text, nullable=False)
    check_type = db.Column(db.Text, nullable=False)
    config_json = db.Column(db.JSON, nullable=False, default=dict)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class BattleTask(db.Model):
    __tablename__ = "battle_tasks"

    battle_id = db.Column(UUID(as_uuid=True), db.ForeignKey("battles.id"), primary_key=True)
    task_id = db.Column(UUID(as_uuid=True), db.ForeignKey("tasks.id"), primary_key=True)
