import re
from sqlalchemy import or_
from ..extensions import db
from ..models import Battle, BattleMember, User, QueueEntry, Match, Room, MatchParticipant
from .scoring_service import lock_scoring


def normalize_invite(value):
    if not isinstance(value, str):
        return None
    code = value.strip().upper()
    return code if re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{3,31}", code) else None


def admit(user, *, code=None, battle_id=None):
    """Persist admission independently from transient matchmaking rows."""
    lock_scoring()
    db.session.query(User).filter_by(id=user.id).with_for_update().first()
    battle = (Battle.query.filter_by(id=battle_id).first() if battle_id
              else Battle.query.filter_by(invite_code=normalize_invite(code)).first() if normalize_invite(code) else None)
    if not battle:
        return None, ("Инвайт не найден. Проверьте код преподавателя.", 404)
    member = db.session.get(BattleMember, (battle.id, user.id))
    if not member and (not battle.invite_code or normalize_invite(code) != battle.invite_code):
        return None, ("Для входа нужен инвайт преподавателя.", 403)
    if battle.status not in {"lobby_open", "running"}:
        return None, ("Батл сейчас закрыт для входа.", 409)
    other_queue = QueueEntry.query.join(Battle).filter(
        QueueEntry.user_id == user.id, QueueEntry.battle_id != battle.id,
        Battle.status.in_(["lobby_open", "running"])).first()
    active = db.session.query(Match.id).join(Room).join(MatchParticipant).filter(
        MatchParticipant.student_id == user.id, Match.finished_at.is_(None),
        MatchParticipant.accepted_at.is_(None),
        or_(MatchParticipant.result_type.is_(None), MatchParticipant.result_type != 'loss')).first()
    if other_queue or active:
        return None, ("Сначала завершите текущий раунд или выйдите из другого лобби.", 409)
    if not member:
        db.session.add(BattleMember(battle_id=battle.id, user_id=user.id))
    entry = QueueEntry.query.filter_by(battle_id=battle.id, user_id=user.id).first()
    if not entry:
        db.session.add(QueueEntry(battle_id=battle.id, user_id=user.id, is_ready=False))
    db.session.commit()
    return battle, None
