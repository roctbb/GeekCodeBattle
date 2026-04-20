from flask import Blueprint, session
from sqlalchemy import or_

from ..api.responses import ok, fail
from ..auth import login_required, role_required
from ..services import queue_service, matchmaker_service, realtime_service, presence_runtime
from ..models import QueueEntry, User, MatchParticipant, Match, Room
from ..extensions import db


queue_bp = Blueprint("queue", __name__, url_prefix="/api/v1")


@queue_bp.get("/battles/<battle_id>/queue")
@login_required
def queue_state(battle_id):
    battle = queue_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Battle not found", 404)
    queue_rows = (
        db.session.query(QueueEntry, User)
        .join(User, User.id == QueueEntry.user_id)
        .filter(QueueEntry.battle_id == battle.id)
        .order_by(QueueEntry.enqueued_at.asc())
        .all()
    )

    queue_by_user = {e.user_id: (e, u) for e, u in queue_rows}
    active_rows = (
        db.session.query(MatchParticipant.student_id, Match.id, Room.id, MatchParticipant.is_disconnected)
        .join(Match, Match.id == MatchParticipant.match_id)
        .join(Room, Room.id == Match.room_id)
        .filter(
            Room.battle_id == battle.id,
            Room.status == "active",
            Match.finished_at.is_(None),
            MatchParticipant.accepted_at.is_(None),
            or_(MatchParticipant.result_type.is_(None), MatchParticipant.result_type != "loss"),
        )
        .all()
    )
    active_by_user = {
        student_id: {"match_id": str(match_id), "room_id": str(room_id), "is_online": not bool(is_disconnected)}
        for student_id, match_id, room_id, is_disconnected in active_rows
    }

    user_ids = set(queue_by_user.keys()) | set(active_by_user.keys())
    users = {}
    if user_ids:
        users = {
            u.id: u
            for u in db.session.query(User).filter(User.id.in_(list(user_ids))).all()
        }

    all_entries = []
    for uid in user_ids:
        queue_info = queue_by_user.get(uid)
        active_info = active_by_user.get(uid)
        user = users.get(uid) or (queue_info[1] if queue_info else None)
        if user is None:
            continue

        if active_info:
            status = "fighting"
            is_ready = False
            enqueued_at = queue_info[0].enqueued_at.isoformat() if queue_info else None
        else:
            is_ready = bool(queue_info[0].is_ready) if queue_info else False
            status = "ready" if is_ready else "not_ready"
            enqueued_at = queue_info[0].enqueued_at.isoformat() if queue_info else None

        all_entries.append(
            {
                "user_id": str(uid),
                "name": user.name,
                "rating": user.rating,
                "status": status,
                "is_ready": is_ready,
                "is_fighting": status == "fighting",
                "is_online": active_info.get("is_online") if active_info else presence_runtime.is_online(str(uid)),
                "enqueued_at": enqueued_at,
                "match_id": active_info.get("match_id") if active_info else None,
                "room_id": active_info.get("room_id") if active_info else None,
            }
        )

    status_rank = {"fighting": 0, "ready": 1, "not_ready": 2}
    all_entries.sort(key=lambda x: (status_rank.get(x.get("status"), 9), x.get("name", "").lower()))

    return ok(
        {
            "battle_id": str(battle.id),
            "status": battle.status,
            "entries": all_entries,
        }
    )


@queue_bp.post("/battles/<battle_id>/queue/join")
@role_required("student")
def queue_join(battle_id):
    battle = queue_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Battle not found", 404)

    entry, created = queue_service.join_queue(battle_id=battle_id, user_id=session["user_id"])
    realtime_service.emit_queue_updated(battle.id, {"battle_id": str(battle.id)})
    return ok({"status": "joined" if created else "already_joined", "id": str(entry.id), "created_rooms": []})


@queue_bp.post("/battles/<battle_id>/queue/leave")
@role_required("student")
def queue_leave(battle_id):
    battle = queue_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Battle not found", 404)

    removed = queue_service.leave_queue(battle_id=battle_id, user_id=session["user_id"])
    realtime_service.emit_queue_updated(battle.id, {"battle_id": str(battle.id)})
    return ok({"status": "left" if removed else "not_in_queue"})


@queue_bp.post("/battles/<battle_id>/queue/ready")
@role_required("student")
def queue_ready(battle_id):
    battle = queue_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Battle not found", 404)

    entry = queue_service.set_ready(battle_id=battle_id, user_id=session["user_id"])
    if not entry:
        return fail("Join queue first", 400)
    created_rooms = matchmaker_service.run_matchmaking(battle.id) if battle.status == "running" else []
    realtime_service.emit_queue_updated(battle.id, {"battle_id": str(battle.id)})
    for room in created_rooms:
        realtime_service.emit_match_found(room)
    return ok({"status": "ready", "created_rooms": created_rooms})
