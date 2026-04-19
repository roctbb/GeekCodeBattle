from sqlalchemy.dialects.postgresql import UUID

from ..extensions import db
from .base import UUIDPKMixin, utcnow


class ScoreEvent(UUIDPKMixin, db.Model):
    __tablename__ = "score_events"

    match_id = db.Column(UUID(as_uuid=True), db.ForeignKey("matches.id"), nullable=False)
    student_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)
    points_delta = db.Column(db.Integer, nullable=False)
    rating_delta = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class RatingHistory(UUIDPKMixin, db.Model):
    __tablename__ = "rating_history"

    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)
    match_id = db.Column(UUID(as_uuid=True), db.ForeignKey("matches.id"), nullable=False)
    old_rating = db.Column(db.Integer, nullable=False)
    new_rating = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
