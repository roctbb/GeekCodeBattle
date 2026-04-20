from __future__ import annotations

from datetime import datetime, timezone, timedelta
from math import pow
from flask import current_app

from ..extensions import db
from ..models import Match, MatchParticipant, Room, User, ScoreEvent, RatingHistory, QueueEntry

K_FACTOR = 24


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


def _apply_streaks(user: User, result_type: str):
    if result_type == "win":
        user.win_streak += 1
        user.loss_streak = 0
    elif result_type == "loss":
        user.loss_streak += 1
        user.win_streak = 0
    elif result_type == "draw":
        user.win_streak = 0
        user.loss_streak = 0


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

    accepted = [p for p in participants if p.accepted_at is not None]
    if accepted:
        accepted.sort(key=lambda p: p.accepted_at)
        leader_ts = accepted[0].accepted_at
        leaders = [p for p in accepted if p.accepted_at == leader_ts]
        if len(leaders) == 1:
            leaders[0].result_type = "win"
            for p in participants:
                if p is not leaders[0]:
                    p.result_type = "loss"
        else:
            for p in participants:
                p.result_type = "draw" if p in leaders else "loss"
    else:
        max_progress = max(float(p.progress or 0) for p in participants) if participants else 0
        if max_progress == 0 and finished_by in {"all_disconnected"}:
            for p in participants:
                p.result_type = "no_result"
        else:
            leaders = [p for p in participants if float(p.progress or 0) == max_progress]
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
            p.accepted_at or datetime.max.replace(tzinfo=timezone.utc),
            -float(p.progress or 0),
        ),
    )
    for idx, p in enumerate(ordered, start=1):
        p.place = idx


def get_winner_info(participants: list[MatchParticipant]):
    accepted = [p for p in participants if p.accepted_at is not None]
    if not accepted:
        return None, None, None
    accepted.sort(key=lambda p: p.accepted_at)
    winner_ts = _as_utc(accepted[0].accepted_at)
    winners = [p for p in accepted if _as_utc(p.accepted_at) == winner_ts]
    winner = winners[0] if len(winners) == 1 else None
    return winner, winner_ts, winners


def get_grace_minutes() -> int:
    return int(current_app.config.get("POST_WIN_GRACE_MINUTES", 5))


def get_grace_deadline(participants: list[MatchParticipant]):
    winner, winner_ts, _ = get_winner_info(participants)
    if winner is None or winner_ts is None:
        return None
    return winner_ts + timedelta(minutes=get_grace_minutes())


def _is_non_winner_resolved(p: MatchParticipant):
    # `result_type=loss` is used as explicit surrender marker before finalization.
    return p.accepted_at is not None or (p.result_type == "loss")


def try_finalize_after_submission(match: Match):
    if match is None or match.finished_at is not None:
        return False

    participants = MatchParticipant.query.filter_by(match_id=match.id).all()
    if not participants:
        finalize_match(match, finished_by="accepted")
        return True

    winner, winner_ts, winners = get_winner_info(participants)
    if winner_ts is None:
        return False

    # Simultaneous accepts are treated as immediate draw resolution.
    if len(winners) > 1:
        finalize_match(match, finished_by="accepted")
        return True

    all_resolved = all((p.student_id == winner.student_id) or _is_non_winner_resolved(p) for p in participants)
    grace_deadline = winner_ts + timedelta(minutes=get_grace_minutes())
    now = datetime.now(timezone.utc)

    if all_resolved:
        finalize_match(match, finished_by="accepted")
        return True

    if now >= grace_deadline:
        finalize_match(match, finished_by="accepted_grace_timeout")
        return True

    return False


def finalize_match(match: Match, finished_by: str = "accepted") -> Match:
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
        db.session.commit()
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

    for p in participants:
        user = users[p.student_id]
        if user is None:
            continue
        rating_delta = int(round(raw_rating_delta[p.student_id] / norm))
        old_rating = user.rating
        user.rating = max(0, user.rating + rating_delta)

        progress = float(p.progress or 0)
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
        from ..models import Battle

        battle = db.session.get(Battle, battle_id)
        if battle and battle.status == "running":
            for p in participants:
                existing = QueueEntry.query.filter_by(battle_id=battle.id, user_id=p.student_id).first()
                if not existing:
                    db.session.add(QueueEntry(battle_id=battle.id, user_id=p.student_id, is_ready=False))
                else:
                    existing.is_ready = False

    db.session.commit()
    return locked_match
