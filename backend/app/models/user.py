from ..extensions import db
from .base import UUIDPKMixin, utcnow


class User(UUIDPKMixin, db.Model):
    __tablename__ = "users"

    external_id = db.Column(db.Text, unique=True, nullable=False)
    name = db.Column(db.Text, nullable=False)
    role = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False, default=1000)
    season_points = db.Column(db.Integer, nullable=False, default=0)
    win_streak = db.Column(db.Integer, nullable=False, default=0)
    loss_streak = db.Column(db.Integer, nullable=False, default=0)
    last_opponents_json = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
