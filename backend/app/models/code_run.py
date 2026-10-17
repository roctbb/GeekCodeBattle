from sqlalchemy.dialects.postgresql import UUID

from ..extensions import db
from .base import UUIDPKMixin, utcnow


class CodeRun(UUIDPKMixin, db.Model):
    """Sandboxed practice executions. Deliberately separate from the score ledger."""
    __tablename__ = "code_runs"

    match_id = db.Column(UUID(as_uuid=True), db.ForeignKey("matches.id"), nullable=False, index=True)
    student_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)
    language = db.Column(db.Text, nullable=False)
    source_code = db.Column(db.Text, nullable=False)
    kind = db.Column(db.Text, nullable=False)
    tests = db.Column(db.JSON, nullable=False)
    verdict = db.Column(db.Text, nullable=False, default="queued")
    checker_comment_raw = db.Column(db.Text, nullable=True)
    checker_status_raw = db.Column(db.Text, nullable=True)
    external_run_id = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
