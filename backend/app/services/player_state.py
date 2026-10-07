from sqlalchemy import or_

from ..extensions import db
from ..models import Match, MatchParticipant, Room, QueueEntry, Battle, BattleMember, Task, ScoreEvent
from .scoring_service import get_winner_info


def player_state(user):
    base = (db.session.query(MatchParticipant, Match, Room)
            .join(Match, Match.id == MatchParticipant.match_id)
            .join(Room, Room.id == Match.room_id)
            .filter(MatchParticipant.student_id == user.id))
    active = base.filter(Match.finished_at.is_(None), Room.status == 'active',
                         MatchParticipant.accepted_at.is_(None),
                         or_(MatchParticipant.result_type.is_(None), MatchParticipant.result_type != 'loss'))\
        .order_by(Match.created_at.desc()).first()
    queued = (QueueEntry.query.join(Battle).filter(QueueEntry.user_id == user.id,
               Battle.status.in_(['lobby_open', 'running']))
              .order_by(QueueEntry.enqueued_at.desc()).first())
    latest = base.filter(or_(Match.finished_at.is_not(None), MatchParticipant.accepted_at.is_not(None),
                            MatchParticipant.result_type == 'loss')).order_by(Match.created_at.desc()).first()
    last_result = None
    if latest:
        p, match, room = latest
        result = p.result_type
        if match.finished_at is None and p.accepted_at is not None:
            winner, _, winners = get_winner_info(MatchParticipant.query.filter_by(match_id=match.id).all())
            result = 'win' if winner and winner.student_id == user.id else (
                'draw' if len(winners or []) > 1 and p in winners else 'loss')
        task = db.session.get(Task, match.task_id)
        points = db.session.query(db.func.coalesce(db.func.sum(ScoreEvent.points_delta), 0)).filter_by(
            match_id=match.id, student_id=user.id).scalar()
        last_result = {'match_id': str(match.id), 'battle_id': str(room.battle_id),
                       'task_title': task.title if task else 'Раунд', 'result_type': result,
                       'points': int(points), 'place': p.place, 'is_final': match.finished_at is not None}
    recent_result = (Battle.query.join(BattleMember).filter(BattleMember.user_id == user.id,
                     Battle.status.in_(['stopped', 'finished']))
                     .order_by(Battle.stopped_at.desc(), Battle.created_at.desc()).first())
    return {
        'result_battle_id': str(recent_result.id) if recent_result else None,
        'room_id': str(active[2].id) if active else None,
        'match_id': str(active[1].id) if active else None,
        'battle_id': str(active[2].battle_id) if active else (str(queued.battle_id) if queued else None),
        'last_result': last_result,
    }
