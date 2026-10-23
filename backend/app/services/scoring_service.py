from __future__ import annotations

from datetime import datetime, timezone, timedelta
from math import pow
from flask import current_app
from sqlalchemy import text

from ..extensions import db
from ..models import Match, MatchParticipant, Room, User, ScoreEvent, RatingHistory, QueueEntry
from .streaks import battle_streaks, apply_streaks as _apply_streaks, INSTANT_WIN_REASON

K_FACTOR = 24
SURRENDER_BONUS_REASON = "match_surrender_solve_bonus"
SURRENDER_AFTER_SECONDS = 10 * 60
SURRENDER_SOLVE_BONUS = 20


def lock_scoring():
    """Serialize score ledger writes, including corrections, across worker processes."""
    if db.session.get_bind().dialect.name == "postgresql":
        db.session.execute(text("SELECT pg_advisory_xact_lock(76432101)"))


RESULT_ORDER = {
    "win": 3,
    "draw": 2,
    "loss": 1,
    "no_result": 0,
}


def _expected(r_you: int, r_opp: int) -> float:
    return 1.0 / (1.0 + pow(10, (r_opp - r_you) / 400.0))


def _pair_score(a_result: str, b_result: str):
    if a_result == "no_result" or b_result == "no_result":
        return None
    if RESULT_ORDER[a_result] > RESULT_ORDER[b_result]:
        return 1.0
    if RESULT_ORDER[a_result] < RESULT_ORDER[b_result]:
        return 0.0
    return 0.5


def _as_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _points_for_result(result_type: str, progress: float, user: User) -> tuple[int, int]:
    base = {
        "win": 100,
        "draw": 60,
        "loss": 30,
        "no_result": 0,
    }[result_type]
    partial = int(max(0.0, min(1.0, progress)) * 40)

    bonus = 0
    if result_type == "win":
        if user.win_streak >= 3:
            bonus = 30
        elif user.win_streak == 2:
            bonus = 20
        elif user.win_streak == 1:
            bonus = 10
        if user.loss_streak >= 3:
            bonus = min(30, bonus + 20)
    bonus = min(30, bonus)

    return base + partial + bonus, bonus


def surrender_available_at(room: Room, participants=()):
    if not room.started_at:
        return None
    started = _as_utc(room.started_at)
    deadline = started + timedelta(seconds=SURRENDER_AFTER_SECONDS)
    accepted = [_as_utc(p.accepted_at) for p in participants
                if p.accepted_at is not None and p.surrendered_at is None]
    return max(started, min(deadline, min(accepted))) if accepted else deadline


def solve_after_surrender_bonus(participant, participants):
    accepted_at = _as_utc(participant.accepted_at)
    if accepted_at is None or participant.surrendered_at is not None:
        return 0
    return SURRENDER_SOLVE_BONUS if any(
        p.student_id != participant.student_id and p.surrendered_at is not None
        and _as_utc(p.surrendered_at) <= accepted_at for p in participants
    ) else 0


def return_to_lobby(battle_id, participants, match_id):
    """An older round finishing must not disturb a player's newer room or readiness."""
    from ..models import Battle
    battle = db.session.get(Battle, battle_id)
    if not battle or battle.status != "running":
        return
    for p in participants:
        other_active = (db.session.query(MatchParticipant.id)
            .join(Match, Match.id == MatchParticipant.match_id)
            .join(Room, Room.id == Match.room_id)
            .filter(MatchParticipant.student_id == p.student_id, Match.id != match_id,
                    Match.finished_at.is_(None), Room.status == "active",
                    MatchParticipant.accepted_at.is_(None), MatchParticipant.surrendered_at.is_(None),
                    db.or_(MatchParticipant.result_type.is_(None), MatchParticipant.result_type != "loss"))
            .first())
        if not other_active and not QueueEntry.query.filter_by(battle_id=battle_id, user_id=p.student_id).first():
            db.session.add(QueueEntry(battle_id=battle_id, user_id=p.student_id, is_ready=False))


def _resolve_results(participants: list[MatchParticipant], finished_by: str):
    if finished_by == "timeout":
        for p in participants:
            p.result_type = "loss"
        ordered = sorted(
            participants,
            key=lambda p: (
                p.accepted_at or datetime.max.replace(tzinfo=timezone.utc),
                -float(p.progress or 0),
            ),
        )
        for idx, p in enumerate(ordered, start=1):
            p.place = idx
        return

    accepted = [p for p in participants if p.accepted_at is not None and p.surrendered_at is None]
    if accepted:
        accepted.sort(key=lambda p: _as_utc(p.accepted_at))
        leader_ts = _as_utc(accepted[0].accepted_at)
        leaders = [p for p in accepted if _as_utc(p.accepted_at) == leader_ts]
        if len(leaders) == 1:
            leaders[0].result_type = "win"
            for p in participants:
                if p is not leaders[0]:
                    p.result_type = "loss"
        else:
            for p in participants:
                p.result_type = "draw" if p in leaders else "loss"
    else:
        contenders = [p for p in participants if p.surrendered_at is None]
        max_progress = max((float(p.progress or 0) for p in contenders), default=0)
        if not contenders:
            for p in participants:
                p.result_type = "loss"
        elif max_progress == 0 and finished_by in {"all_disconnected"}:
            for p in participants:
                p.result_type = "no_result"
        else:
            leaders = [p for p in contenders if float(p.progress or 0) == max_progress]
            if len(leaders) == len(participants):
                for p in participants:
                    p.result_type = "draw"
            else:
                for p in participants:
                    p.result_type = "draw" if p in leaders and len(leaders) > 1 else ("win" if p in leaders else "loss")

    # Stable place: result_type first, then accepted_at, then progress.
    ordered = sorted(
        participants,
        key=lambda p: (
            -RESULT_ORDER.get(p.result_type or "no_result", 0),
            _as_utc(p.accepted_at) or datetime.max.replace(tzinfo=timezone.utc),
            -float(p.progress or 0),
        ),
    )
    for idx, p in enumerate(ordered, start=1):
        p.place = idx


def get_winner_info(participants: list[MatchParticipant]):
    accepted = [p for p in participants if p.accepted_at is not None and p.surrendered_at is None]
    if not accepted:
        return None, None, None
    accepted.sort(key=lambda p: _as_utc(p.accepted_at))
    winner_ts = _as_utc(accepted[0].accepted_at)
    winners = [p for p in accepted if _as_utc(p.accepted_at) == winner_ts]
    winner = winners[0] if len(winners) == 1 else None
    return winner, winner_ts, winners


def try_finalize_after_submission(match: Match):
    if match is None or match.finished_at is not None:
        return False

    participants = MatchParticipant.query.filter_by(match_id=match.id).all()
    if not participants:
        finalize_match(match, finished_by="accepted")
        return True

    all_resolved = all(p.accepted_at is not None or p.surrendered_at is not None or p.result_type == "loss" for p in participants)
    if all_resolved:
        finalize_match(match, finished_by="accepted" if any(p.accepted_at for p in participants) else "surrendered")
        return True

    return False


def award_instant_winner_points(match: Match, student_id) -> int:
    lock_scoring()
    if match is None or student_id is None:
        return 0

    locked_match = (
        db.session.query(Match)
        .filter(Match.id == match.id)
        .with_for_update()
        .first()
    )
    if locked_match is None or locked_match.finished_at is not None:
        return 0

    participants = (
        db.session.query(MatchParticipant)
        .filter(MatchParticipant.match_id == locked_match.id)
        .with_for_update()
        .all()
    )
    winner, _, winners = get_winner_info(participants)
    if winner is None or len(winners) != 1 or str(winner.student_id) != str(student_id):
        return 0

    existing = (
        db.session.query(ScoreEvent.id)
        .filter(
            ScoreEvent.match_id == locked_match.id,
            ScoreEvent.student_id == winner.student_id,
            ScoreEvent.reason == INSTANT_WIN_REASON,
        )
        .limit(1)
        .first()
    )
    if existing:
        return 0

    user = (
        db.session.query(User)
        .filter(User.id == winner.student_id)
        .with_for_update()
        .first()
    )
    if user is None:
        return 0

    progress = float(winner.progress or 0)
    room = db.session.get(Room, locked_match.room_id)
    streak = battle_streaks(room.battle_id, [user.id])[user.id]
    user.win_streak, user.loss_streak = streak.win_streak, streak.loss_streak
    points_delta, _ = _points_for_result("win", progress, user)
    user.season_points = max(0, user.season_points + points_delta)
    _apply_streaks(user, "win")
    db.session.add(
        ScoreEvent(
            match_id=locked_match.id,
            student_id=user.id,
            points_delta=points_delta,
            rating_delta=0,
            reason=INSTANT_WIN_REASON,
        )
    )
    db.session.commit()
    return points_delta


def finalize_match(match: Match, finished_by: str = "accepted", *, commit=True) -> Match:
    lock_scoring()
    locked_match = (
        db.session.query(Match)
        .filter(Match.id == match.id)
        .with_for_update()
        .first()
    )
    if locked_match is None:
        return match
    if locked_match.finished_at is not None:
        return locked_match

    participants = (
        db.session.query(MatchParticipant)
        .filter(MatchParticipant.match_id == locked_match.id)
        .with_for_update()
        .all()
    )
    if not participants:
        locked_match.finished_by = finished_by
        locked_match.finished_at = datetime.now(timezone.utc)
        room = db.session.get(Room, locked_match.room_id)
        if room:
            room.status = "finished"
            room.finished_at = locked_match.finished_at
        db.session.commit() if commit else db.session.flush()
        return locked_match

    # Idempotency guard for legacy/inconsistent states:
    # if match-level scoring artifacts already exist, do not apply deltas again.
    existing_score_artifacts = (
        db.session.query(RatingHistory.id)
        .filter(RatingHistory.match_id == locked_match.id)
        .limit(1)
        .first()
        is not None
    ) or (
        db.session.query(ScoreEvent.id)
        .filter(
            ScoreEvent.match_id == locked_match.id,
            ScoreEvent.reason.like("match_finalize:%"),
        )
        .limit(1)
        .first()
        is not None
    )
    if existing_score_artifacts:
        now = datetime.now(timezone.utc)
        if locked_match.finished_at is None:
            locked_match.finished_by = finished_by
            locked_match.finished_at = now

        room = db.session.get(Room, locked_match.room_id)
        if room and room.status != "finished":
            room.status = "finished"
            room.finished_at = now

        db.session.flush()

        battle_id = room.battle_id if room else None
        if battle_id is not None:
            return_to_lobby(battle_id, participants, locked_match.id)

        current_app.logger.warning(
            "finalize_match_idempotent_skip match_id=%s finished_by=%s",
            locked_match.id,
            finished_by,
        )
        db.session.commit() if commit else db.session.flush()
        return locked_match

    _resolve_results(participants, finished_by)

    user_ids = list({p.student_id for p in participants})
    users = {}
    if user_ids:
        users = {
            user.id: user
            for user in (
                db.session.query(User)
                .filter(User.id.in_(user_ids))
                .with_for_update()
                .all()
            )
        }

    # Pairwise Elo aggregation.
    raw_rating_delta = {p.student_id: 0.0 for p in participants}
    for i in range(len(participants)):
        for j in range(i + 1, len(participants)):
            a = participants[i]
            b = participants[j]
            sa = _pair_score(a.result_type, b.result_type)
            if sa is None:
                continue
            ua = users[a.student_id]
            ub = users[b.student_id]
            ea = _expected(ua.rating, ub.rating)
            eb = _expected(ub.rating, ua.rating)
            sb = 1.0 - sa
            raw_rating_delta[a.student_id] += K_FACTOR * (sa - ea)
            raw_rating_delta[b.student_id] += K_FACTOR * (sb - eb)

    norm = max(1, len(participants) - 1)
    instant_win_student_ids = {
        student_id
        for (student_id,) in (
            db.session.query(ScoreEvent.student_id)
            .filter(
                ScoreEvent.match_id == locked_match.id,
                ScoreEvent.reason == INSTANT_WIN_REASON,
            )
            .all()
        )
    }

    room = db.session.get(Room, locked_match.room_id)
    streaks = battle_streaks(room.battle_id, user_ids)
    for p in participants:
        user = users[p.student_id]
        if user is None:
            continue
        rating_delta = int(round(raw_rating_delta[p.student_id] / norm))
        old_rating = user.rating
        user.rating = max(0, user.rating + rating_delta)

        points_delta = 0
        if (p.student_id in instant_win_student_ids) and ((p.result_type or "no_result") == "win"):
            points_delta = 0
        else:
            progress = float(p.progress or 0)
            streak = streaks[p.student_id]
            user.win_streak, user.loss_streak = streak.win_streak, streak.loss_streak
            points_delta, _ = _points_for_result(p.result_type or "no_result", progress, user)
            user.season_points = max(0, user.season_points + points_delta)
            _apply_streaks(user, p.result_type or "no_result")

        db.session.add(
            RatingHistory(
                user_id=user.id,
                match_id=locked_match.id,
                old_rating=old_rating,
                new_rating=user.rating,
            )
        )
        db.session.add(
            ScoreEvent(
                match_id=locked_match.id,
                student_id=user.id,
                points_delta=points_delta,
                rating_delta=rating_delta,
                reason=f"match_finalize:{p.result_type}",
            )
        )
        surrender_bonus = solve_after_surrender_bonus(p, participants)
        if surrender_bonus:
            user.season_points += surrender_bonus
            db.session.add(ScoreEvent(match_id=locked_match.id, student_id=user.id,
                                      points_delta=surrender_bonus, rating_delta=0,
                                      reason=SURRENDER_BONUS_REASON))

    locked_match.finished_by = finished_by
    locked_match.finished_at = datetime.now(timezone.utc)

    room = db.session.get(Room, locked_match.room_id)
    if room and room.status != "finished":
        room.status = "finished"
        room.finished_at = datetime.now(timezone.utc)

    db.session.flush()

    # Keep players in lobby after round finish: they must press "Ready" again.
    battle_id = room.battle_id if room else None
    if battle_id is not None:
        return_to_lobby(battle_id, participants, locked_match.id)

    db.session.commit() if commit else db.session.flush()
    return locked_match
