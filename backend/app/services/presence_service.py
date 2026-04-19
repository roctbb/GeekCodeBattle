from datetime import datetime, timezone

from ..extensions import db
from ..models import MatchParticipant, Match, Room
from ..utils import as_uuid


def set_user_online(user_id):
    return _set_user_connection_state(user_id, is_connected=True)


def set_user_offline(user_id):
    return _set_user_connection_state(user_id, is_connected=False)


def _set_user_connection_state(user_id, *, is_connected: bool):
    if not user_id:
        return {"changed": False, "battle_ids": [], "room_ids": [], "match_ids": []}

    user_uuid = as_uuid(user_id)
    now = datetime.now(timezone.utc)
    rows = (
        db.session.query(MatchParticipant, Match, Room)
        .join(Match, Match.id == MatchParticipant.match_id)
        .join(Room, Room.id == Match.room_id)
        .filter(MatchParticipant.student_id == user_uuid, Match.finished_at.is_(None))
        .all()
    )
    if not rows:
        return {"changed": False, "battle_ids": [], "room_ids": [], "match_ids": []}

    changed = False
    battle_ids = set()
    room_ids = set()
    match_ids = set()
    for participant, match, room in rows:
        battle_ids.add(str(room.battle_id))
        room_ids.add(str(room.id))
        match_ids.add(str(match.id))

        if is_connected:
            if participant.is_disconnected or participant.disconnected_at is not None:
                participant.is_disconnected = False
                participant.disconnected_at = None
                changed = True
        else:
            if not participant.is_disconnected:
                participant.is_disconnected = True
                participant.disconnected_at = now
                changed = True
            elif participant.disconnected_at is None:
                participant.disconnected_at = now
                changed = True

    if changed:
        db.session.commit()

    return {
        "changed": changed,
        "battle_ids": sorted(battle_ids),
        "room_ids": sorted(room_ids),
        "match_ids": sorted(match_ids),
    }
