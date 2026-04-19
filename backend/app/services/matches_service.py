from ..extensions import db
from ..models import Match, MatchParticipant, AuditLog
from ..utils import as_uuid


def get_match_or_none(match_id):
    return db.session.get(Match, as_uuid(match_id))


def get_match_participants(match_id):
    return MatchParticipant.query.filter_by(match_id=as_uuid(match_id)).all()


def rejudge_match(*, match_id, actor_id, reason, new_results):
    match = get_match_or_none(match_id)
    if not match:
        return None, "match_not_found"

    participants = get_match_participants(match_id)
    expected_ids = {str(p.student_id) for p in participants}
    incoming_ids = {str(item.get("student_id")) for item in new_results}
    if incoming_ids != expected_ids:
        return None, "missing_participants"

    for item in new_results:
        p = next(x for x in participants if str(x.student_id) == str(item["student_id"]))
        p.result_type = item["result_type"]

    log = AuditLog(
        actor_id=as_uuid(actor_id),
        entity_type="match",
        entity_id=match.id,
        action="rejudge",
        payload_json={"reason": reason, "new_results": new_results},
    )
    db.session.add(log)
    db.session.commit()
    return match, None
