"""Object-level access shared by HTTP routes and realtime subscriptions."""
from .extensions import db
from .models import Battle, BattleMember, Room, Match, MatchParticipant
from .utils import as_uuid


def is_battle_member(user, battle):
    return bool(user and battle and db.session.get(BattleMember, (battle.id, user.id)))


def can_read_battle(user, battle):
    return bool(user and battle and (user.role in {"teacher", "admin"} or is_battle_member(user, battle)))


def can_read_match(user, match):
    return bool(user and match and (
        user.role in {"teacher", "admin"}
        or MatchParticipant.query.filter_by(match_id=match.id, student_id=user.id).first()
    ))


def can_read_room(user, room):
    if not user or not room:
        return False
    if user.role in {"teacher", "admin"}:
        return True
    return db.session.query(MatchParticipant.id).join(Match).filter(
        Match.room_id == room.id, MatchParticipant.student_id == user.id,
    ).first() is not None


def allowed_scopes(user, data):
    result = {}
    for key, model, check in (
        ("battle_id", Battle, can_read_battle),
        ("room_id", Room, can_read_room),
        ("match_id", Match, can_read_match),
    ):
        value = data.get(key)
        if not value:
            result[key] = None
            continue
        try:
            obj = db.session.get(model, as_uuid(value))
        except (ValueError, TypeError, AttributeError):
            return None
        if not check(user, obj):
            return None
        result[key] = str(obj.id)
    return result
