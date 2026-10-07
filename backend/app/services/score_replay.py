"""Deterministic corrections of the retained ledger, without deleting original events."""
from collections import defaultdict
from types import SimpleNamespace

from ..extensions import db
from ..models import Match, MatchParticipant, ScoreEvent, RatingHistory, User
from .scoring_service import INSTANT_WIN_REASON, K_FACTOR, _as_utc, _expected, _pair_score, _points_for_result, _apply_streaks

CORRECTION_REASON = "match_rejudge"


def replay_scores():
    events = ScoreEvent.query.order_by(ScoreEvent.created_at, ScoreEvent.id).all()
    histories = RatingHistory.query.order_by(RatingHistory.created_at, RatingHistory.id).all()
    totals = defaultdict(int)
    original_totals = defaultdict(int)
    original_ratings = defaultdict(int)
    corrections = {}
    instant = {}
    for event in events:
        key = (event.match_id, event.student_id)
        totals[key] += event.points_delta
        if event.reason == CORRECTION_REASON:
            corrections[key] = event
        else:
            original_totals[key] += event.points_delta
            original_ratings[key] += event.rating_delta
        if event.reason == INSTANT_WIN_REASON:
            instant[key] = event

    user_ids = {uid for _, uid in totals}
    if not user_ids:
        return {}
    users = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).order_by(User.id).with_for_update().all()}
    baseline_ratings = {}
    history_map = {}
    for h in histories:
        baseline_ratings.setdefault(h.user_id, h.old_rating)
        history_map[(h.match_id, h.user_id)] = h
    points_by_user = defaultdict(int)
    for (_, uid), value in totals.items():
        points_by_user[uid] += value
    states = {
        uid: SimpleNamespace(rating=baseline_ratings.get(uid, u.rating),
                             season_points=u.season_points - points_by_user[uid],
                             win_streak=0, loss_streak=0)
        for uid, u in users.items()
    }
    before = {str(uid): {k: getattr(u, k) for k in ('rating', 'season_points', 'win_streak', 'loss_streak')} for uid, u in users.items()}
    matches = {m.id: m for m in Match.query.filter(Match.id.in_({mid for mid, _ in totals})).all()}
    participants = defaultdict(list)
    for p in MatchParticipant.query.filter(MatchParticipant.match_id.in_(matches)).all():
        participants[p.match_id].append(p)

    actions = []
    desired = defaultdict(int)
    for mid, match in matches.items():
        for p in participants[mid]:
            key = (mid, p.student_id)
            if key not in totals:
                continue
            result = p.result_type or 'no_result'
            early = instant.get(key)
            if match.finished_at is None:
                if not early:
                    continue
                result = 'win'
            stamp = early.created_at if early and result == 'win' else match.finished_at
            actions.append((_as_utc(stamp), 0, str(mid), str(p.student_id), 'points', p, result))
        if match.finished_at is not None:
            # Historical rating writes carry the actual order in which rounds settled.
            h = next((history_map.get((mid, p.student_id)) for p in participants[mid]
                      if (mid, p.student_id) in history_map), None)
            actions.append((_as_utc(h.created_at if h else match.finished_at), 1, str(mid), '', 'rating', match, None))

    for _, _, _, _, kind, item, result in sorted(actions, key=lambda a: a[:4]):
        if kind == 'points':
            state = states[item.student_id]
            delta, _ = _points_for_result(result, float(item.progress or 0), state)
            desired[(item.match_id, item.student_id)] = delta
            state.season_points += delta
            _apply_streaks(state, result)
            continue
        rows = participants[item.id]
        raw = defaultdict(float)
        for i, a in enumerate(rows):
            for b in rows[i + 1:]:
                score = _pair_score(a.result_type or 'no_result', b.result_type or 'no_result')
                if score is None:
                    continue
                ra, rb = states[a.student_id].rating, states[b.student_id].rating
                raw[a.student_id] += K_FACTOR * (score - _expected(ra, rb))
                raw[b.student_id] += K_FACTOR * (1 - score - _expected(rb, ra))
        for p in rows:
            state = states[p.student_id]
            old = state.rating
            state.rating = max(0, old + round(raw[p.student_id] / max(1, len(rows) - 1)))
            h = history_map.get((item.id, p.student_id))
            if h:
                h.old_rating, h.new_rating = old, state.rating

    # Keep original score events for audit; one adjustable compensation per participant.
    for key, target in desired.items():
        delta = target - original_totals[key]
        correction = corrections.get(key)
        if correction:
            correction.points_delta = delta
        elif delta:
            correction = ScoreEvent(match_id=key[0], student_id=key[1], points_delta=delta,
                                    rating_delta=0, reason=CORRECTION_REASON)
            db.session.add(correction)
            corrections[key] = correction
        h = history_map.get(key)
        if h:
            rating_correction = h.new_rating - h.old_rating - original_ratings[key]
            if rating_correction and key not in corrections:
                corrections[key] = ScoreEvent(match_id=key[0], student_id=key[1], points_delta=0,
                                             rating_delta=0, reason=CORRECTION_REASON)
                db.session.add(corrections[key])
            if key in corrections:
                corrections[key].rating_delta = rating_correction

    for uid, state in states.items():
        for name in ('rating', 'season_points', 'win_streak', 'loss_streak'):
            setattr(users[uid], name, getattr(state, name))
    after = {str(uid): vars(state) for uid, state in states.items()}
    return {'before': before, 'after': after}
