from sqlalchemy.dialects.postgresql import UUID

from ..extensions import db
from .base import UUIDPKMixin, utcnow


class AuditLog(UUIDPKMixin, db.Model):
    __tablename__ = "audit_log"

    actor_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)
    entity_type = db.Column(db.Text, nullable=False)
    entity_id = db.Column(UUID(as_uuid=True), nullable=False)
    action = db.Column(db.Text, nullable=False)
    payload_json = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
