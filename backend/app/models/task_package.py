from sqlalchemy.dialects.postgresql import UUID

from ..extensions import db
from .base import UUIDPKMixin, utcnow


class TaskPackage(UUIDPKMixin, db.Model):
    __tablename__ = "task_packages"

    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class TaskPackageTask(db.Model):
    __tablename__ = "task_package_tasks"

    package_id = db.Column(UUID(as_uuid=True), db.ForeignKey("task_packages.id"), primary_key=True)
    task_id = db.Column(UUID(as_uuid=True), db.ForeignKey("tasks.id"), primary_key=True)


class BattleTaskPackage(db.Model):
    __tablename__ = "battle_task_packages"

    battle_id = db.Column(UUID(as_uuid=True), db.ForeignKey("battles.id"), primary_key=True)
    package_id = db.Column(UUID(as_uuid=True), db.ForeignKey("task_packages.id"), primary_key=True)
