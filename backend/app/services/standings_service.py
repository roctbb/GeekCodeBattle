"""One deterministic ranking for leaderboards and personal result context."""
from ..extensions import db
from ..models import BattleMember, User, Match, Room, MatchParticipant, ScoreEvent, RatingHistory
from .rooms_service import _as_utc
from .streaks import battle_streaks


def battle_standings(battle_id, *, at=None):
    members = db.session.query(BattleMember, User).join(User).filter(BattleMember.battle_id == battle_id)
    if at is not None:
        at = _as_utc(at)
        members = members.filter(BattleMember.joined_at <= at)
    members = members.all()
    ids = [user.id for _, user in members]
    scores = db.session.query(ScoreEvent.student_id, db.func.sum(ScoreEvent.points_delta)).join(Match).join(Room).filter(Room.battle_id == battle_id)
    if at is not None:
        scores = scores.filter(ScoreEvent.created_at < at)
    points = dict(scores.group_by(ScoreEvent.student_id).all())
    rewind = {}
    if at is not None and ids:
        rewind = dict(db.session.query(RatingHistory.user_id, db.func.sum(RatingHistory.new_rating - RatingHistory.old_rating))
            .filter(RatingHistory.user_id.in_(ids), RatingHistory.created_at >= at).group_by(RatingHistory.user_id).all())
    streaks = battle_streaks(battle_id, ids, at=at)
    rows = [{"user_id": str(user.id), "name": user.name, "rating": user.rating - int(rewind.get(user.id, 0)),
             "battle_points": int(points.get(user.id, 0)), "season_points": int(points.get(user.id, 0)),
             "win_streak": streaks[user.id].win_streak, "loss_streak": streaks[user.id].loss_streak} for _, user in members]
    rows.sort(key=lambda row: (-row["battle_points"], -row["rating"], row["name"], row["user_id"]))
    for place, row in enumerate(rows, 1):
        row["place"] = place
    return rows


def battle_standing_context(battle_id, user_id):
    rows = battle_standings(battle_id)
    index = next((i for i, row in enumerate(rows) if row["user_id"] == str(user_id)), None)
    if index is None:
        return None
    latest = Match.query.join(Room).join(MatchParticipant).filter(
        Room.battle_id == battle_id, MatchParticipant.student_id == user_id, Match.finished_at.is_not(None)
    ).order_by(Match.finished_at.desc(), Match.id).first()
    previous_place, compared_at = None, None
    if latest:
        compared_at = min(_as_utc(db.session.get(Room, latest.room_id).started_at or latest.created_at), _as_utc(latest.finished_at))
        before = battle_standings(battle_id, at=compared_at)
        previous_place = next((row["place"] for row in before if row["user_id"] == str(user_id)), None)
    return {"place": index + 1, "total": len(rows), "previous_place": previous_place,
            "change": previous_place - index - 1 if previous_place is not None else None,
            "compared_at": compared_at.isoformat() if compared_at else None,
            "neighbors": [{key: row[key] for key in ("user_id", "name", "place", "battle_points", "rating")}
                          for row in rows[max(0, index - 2):index + 3]]}
