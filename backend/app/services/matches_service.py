from ..extensions import db
from ..models import Match, MatchParticipant, AuditLog, Room
from .scoring_service import lock_scoring, RESULT_ORDER, _as_utc
from .score_replay import replay_scores
from datetime import datetime, timezone
from ..utils import as_uuid


def get_match_or_none(match_id):
    return db.session.get(Match, as_uuid(match_id))


def get_match_participants(match_id):
    return MatchParticipant.query.filter_by(match_id=as_uuid(match_id)).all()


def rejudge_match(*, match_id, actor_id, reason, new_results):
    lock_scoring()
    match = get_match_or_none(match_id)
    if not match:
        return None, "match_not_found"

    participants = get_match_participants(match_id)
    expected_ids = {str(p.student_id) for p in participants}
    incoming_ids = {str(item.get("student_id")) for item in new_results}
    if incoming_ids != expected_ids or len(new_results) != len(expected_ids):
        return None, "missing_participants"
    if match.finished_at is None:
        return None, "match_not_finished"

    old_results = [{"student_id": str(p.student_id), "result_type": p.result_type} for p in participants]

    for item in new_results:
        p = next(x for x in participants if str(x.student_id) == str(item["student_id"]))
        p.result_type = item["result_type"]

    ordered = sorted(participants, key=lambda p: (-RESULT_ORDER[p.result_type],
                     _as_utc(p.accepted_at) or datetime.max.replace(tzinfo=timezone.utc),
                     -float(p.progress or 0), str(p.student_id)))
    for place, p in enumerate(ordered, 1):
        p.place = place
    db.session.flush()
    changes = replay_scores()

    log = AuditLog(
        actor_id=as_uuid(actor_id),
        entity_type="match",
        entity_id=match.id,
        action="rejudge",
        payload_json={"reason": reason, "old_results": old_results, "new_results": new_results,
                      "score_changes": changes},
    )
    db.session.add(log)
    db.session.commit()
    from .realtime_service import emit_leaderboard_updated
    for (battle_id,) in db.session.query(Room.battle_id).distinct().all():
        emit_leaderboard_updated(battle_id)
    return match, None
