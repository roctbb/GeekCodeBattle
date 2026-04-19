from sqlalchemy import UniqueConstraint

from sqlalchemy.dialects.postgresql import UUID

from ..extensions import db
from .base import UUIDPKMixin, utcnow


class QueueEntry(UUIDPKMixin, db.Model):
    __tablename__ = "queue_entries"
    __table_args__ = (UniqueConstraint("battle_id", "user_id", name="uq_queue_battle_user"),)

    battle_id = db.Column(UUID(as_uuid=True), db.ForeignKey("battles.id"), nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)
    is_ready = db.Column(db.Boolean, nullable=False, default=False)
    enqueued_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    last_opponents_json = db.Column(db.JSON, nullable=False, default=list)
