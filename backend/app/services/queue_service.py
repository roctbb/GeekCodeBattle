from ..extensions import db
from ..models import Battle, QueueEntry
from ..utils import as_uuid


def get_battle_or_none(battle_id):
    return db.session.get(Battle, as_uuid(battle_id))


def join_queue(*, battle_id, user_id):
    existing = QueueEntry.query.filter_by(battle_id=as_uuid(battle_id), user_id=as_uuid(user_id)).first()
    if existing:
        return existing, False

    entry = QueueEntry(battle_id=as_uuid(battle_id), user_id=as_uuid(user_id), is_ready=False)
    db.session.add(entry)
    db.session.commit()
    return entry, True


def leave_queue(*, battle_id, user_id):
    existing = QueueEntry.query.filter_by(battle_id=as_uuid(battle_id), user_id=as_uuid(user_id)).first()
    if not existing:
        return False
    db.session.delete(existing)
    db.session.commit()
    return True


def set_ready(*, battle_id, user_id):
    existing = QueueEntry.query.filter_by(battle_id=as_uuid(battle_id), user_id=as_uuid(user_id)).first()
    if not existing:
        return None
    existing.is_ready = True
    db.session.commit()
    return existing
