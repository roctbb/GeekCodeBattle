from sqlalchemy import CheckConstraint, UniqueConstraint

from sqlalchemy.dialects.postgresql import UUID

from ..extensions import db
from .base import UUIDPKMixin, utcnow


class Match(UUIDPKMixin, db.Model):
    __tablename__ = "matches"

    room_id = db.Column(UUID(as_uuid=True), db.ForeignKey("rooms.id"), nullable=False)
    task_id = db.Column(UUID(as_uuid=True), db.ForeignKey("tasks.id"), nullable=False)
    finished_by = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)


class MatchParticipant(UUIDPKMixin, db.Model):
    __tablename__ = "match_participants"
    __table_args__ = (
        UniqueConstraint("match_id", "student_id", name="uq_match_student"),
        CheckConstraint("result_type in ('win','draw','loss','no_result') or result_type is null", name="ck_result_type"),
    )

    match_id = db.Column(UUID(as_uuid=True), db.ForeignKey("matches.id"), nullable=False)
    student_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)
    result_type = db.Column(db.Text, nullable=True)
    accepted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    disconnected_at = db.Column(db.DateTime(timezone=True), nullable=True)
    progress = db.Column(db.Numeric(5, 4), nullable=True)
    place = db.Column(db.Integer, nullable=True)
    is_disconnected = db.Column(db.Boolean, nullable=False, default=False)
