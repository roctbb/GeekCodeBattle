from sqlalchemy.dialects.postgresql import UUID

from ..extensions import db
from .base import UUIDPKMixin, utcnow


class Battle(UUIDPKMixin, db.Model):
    __tablename__ = "battles"

    title = db.Column(db.Text, nullable=False)
    status = db.Column(db.Text, nullable=False, default="draft")
    room_size = db.Column(db.Integer, nullable=False, default=2)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
