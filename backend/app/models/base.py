import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID

from ..extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class UUIDPKMixin:
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
