from sqlalchemy.dialects.postgresql import UUID

from ..extensions import db
from .base import UUIDPKMixin, utcnow


class Room(UUIDPKMixin, db.Model):
    __tablename__ = "rooms"

    battle_id = db.Column(UUID(as_uuid=True), db.ForeignKey("battles.id"), nullable=False)
    status = db.Column(db.Text, nullable=False, default="waiting_ready")
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
