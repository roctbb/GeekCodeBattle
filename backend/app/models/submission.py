from sqlalchemy.dialects.postgresql import UUID

from ..extensions import db
from .base import UUIDPKMixin, utcnow


class Submission(UUIDPKMixin, db.Model):
    __tablename__ = "submissions"

    match_id = db.Column(UUID(as_uuid=True), db.ForeignKey("matches.id"), nullable=False)
    student_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)
    language = db.Column(db.Text, nullable=False)
    source_code = db.Column(db.Text, nullable=False)
    verdict = db.Column(db.Text, nullable=False, default="queued")
    progress_value = db.Column(db.Numeric(5, 4), nullable=False, default=0)
    visible_tests_passed = db.Column(db.Integer, nullable=True)
    visible_tests_total = db.Column(db.Integer, nullable=True)
    hidden_tests_passed = db.Column(db.Integer, nullable=True)
    hidden_tests_total = db.Column(db.Integer, nullable=True)
    external_run_id = db.Column(db.Text, nullable=True)
    callback_received_at = db.Column(db.DateTime(timezone=True), nullable=True)
    checker_status_raw = db.Column(db.Text, nullable=True)
    checker_comment_raw = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
