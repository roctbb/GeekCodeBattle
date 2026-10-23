"""Winning and losing streaks belong to one battle, including early wins."""
from types import SimpleNamespace

from sqlalchemy import and_, or_

from ..extensions import db
from ..models import Match, MatchParticipant, Room, ScoreEvent
from ..utils import as_uuid

INSTANT_WIN_REASON = 'match_instant_win'


def apply_streaks(state, result):
    if result == 'win':
        state.win_streak += 1
        state.loss_streak = 0
    elif result == 'loss':
        state.loss_streak += 1
        state.win_streak = 0
    elif result == 'draw':
        state.win_streak = state.loss_streak = 0


def battle_streaks(battle_id, user_ids=None, *, at=None):
    from .rooms_service import _as_utc

    states = {uid: SimpleNamespace(win_streak=0, loss_streak=0) for uid in user_ids or []}
    rows = (db.session.query(MatchParticipant, Match, ScoreEvent)
            .join(Match, Match.id == MatchParticipant.match_id)
            .join(Room, Room.id == Match.room_id)
            .join(ScoreEvent, and_(ScoreEvent.match_id == Match.id,
                                  ScoreEvent.student_id == MatchParticipant.student_id))
            .filter(Room.battle_id == as_uuid(battle_id),
                    or_(ScoreEvent.reason == INSTANT_WIN_REASON, ScoreEvent.reason.like('match_finalize:%'))))
    if user_ids is not None:
        rows = rows.filter(MatchParticipant.student_id.in_(user_ids))
    rounds = {}
    for participant, match, event in rows.all():
        record = rounds.setdefault((participant.student_id, match.id), [participant, match, None])
        if event.reason == INSTANT_WIN_REASON:
            record[2] = event.created_at
    actions = []
    for participant, match, early in rounds.values():
        result = participant.result_type or 'no_result'
        if match.finished_at is None:
            if early is None:
                continue
            result = 'win'
        stamp = _as_utc(early if early is not None and result == 'win' else match.finished_at)
        if at is None or stamp < _as_utc(at):
            actions.append((stamp, str(match.id), str(participant.student_id), participant.student_id, result))
    for _, _, _, uid, result in sorted(actions):
        state = states.setdefault(uid, SimpleNamespace(win_streak=0, loss_streak=0))
        apply_streaks(state, result)
    return states
