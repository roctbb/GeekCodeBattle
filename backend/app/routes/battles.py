from flask import Blueprint, request, session
from sqlalchemy import and_

from ..api.responses import ok, fail
from ..api.serializers import battle_out, task_out, task_package_out
from ..auth import login_required, role_required
from ..services import battles_service, matchmaker_service, realtime_service, presence_runtime
from ..models import MatchParticipant, Match, Room, User, ScoreEvent
from ..extensions import db


battles_bp = Blueprint("battles", __name__, url_prefix="/api/v1")


@battles_bp.get("/battles")
@login_required
def list_battles():
    return ok([battle_out(b) for b in battles_service.list_battles()])


@battles_bp.post("/battles")
@role_required("teacher", "admin")
def create_battle():
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    if not title:
        return fail("title is required", 400)
    room_size = data.get("room_size", 2)
    try:
        room_size = int(room_size)
    except (TypeError, ValueError):
        return fail("room_size must be integer", 400)
    if room_size < 2:
        return fail("room_size must be >= 2", 400)

    package_ids = data.get("package_ids", [])
    if package_ids is None:
        package_ids = []
    if not isinstance(package_ids, list):
        return fail("package_ids must be list", 400)

    battle = battles_service.create_battle(
        title=title,
        created_by=session["user_id"],
        room_size=room_size,
        package_ids=package_ids,
    )
    return ok(battle_out(battle), 201)


@battles_bp.get("/battles/<battle_id>")
@login_required
def get_battle(battle_id):
    battle = battles_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Not found", 404)
    battles_service.tick_timeouts(battle)
    return ok(battle_out(battle))


@battles_bp.patch("/battles/<battle_id>")
@role_required("teacher", "admin")
def update_battle(battle_id):
    battle = battles_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Not found", 404)

    data = request.get_json() or {}
    title = None
    if "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            return fail("title cannot be empty", 400)

    battle = battles_service.update_battle(battle, title=title)
    return ok(battle_out(battle))


@battles_bp.post("/battles/<battle_id>/open-lobby")
@role_required("teacher", "admin")
def open_lobby(battle_id):
    battle = battles_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Not found", 404)
    if battle.status == "finished":
        return fail("Battle is finished", 400)
    opened = battles_service.open_lobby(battle)
    realtime_service.emit_battle_status_changed(opened.id, opened.status)
    return ok(battle_out(opened))


@battles_bp.post("/battles/<battle_id>/start")
@role_required("teacher", "admin")
def start_battle(battle_id):
    battle = battles_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Not found", 404)
    if battle.status not in {"lobby_open", "stopped", "draft"}:
        return fail("Invalid status transition", 400)
    started = battles_service.start_battle(battle)
    created_rooms = matchmaker_service.run_matchmaking(started.id)
    realtime_service.emit_battle_status_changed(started.id, started.status)
    for room in created_rooms:
        realtime_service.emit_match_found(room)
    return ok({"battle": battle_out(started), "created_rooms": created_rooms})


@battles_bp.post("/battles/<battle_id>/stop")
@role_required("teacher", "admin")
def stop_battle(battle_id):
    battle = battles_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Not found", 404)
    if battle.status != "running":
        return fail("Battle is not running", 400)
    stopped = battles_service.stop_battle(battle)
    realtime_service.emit_battle_status_changed(stopped.id, stopped.status)
    realtime_service.emit_leaderboard_updated(stopped.id)
    return ok(battle_out(stopped))


@battles_bp.post("/battles/<battle_id>/finish")
@role_required("teacher", "admin")
def finish_battle(battle_id):
    battle = battles_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Not found", 404)
    finished = battles_service.finish_battle(battle)
    realtime_service.emit_battle_status_changed(finished.id, finished.status)
    realtime_service.emit_leaderboard_updated(finished.id)
    return ok(battle_out(finished))


@battles_bp.delete("/battles/<battle_id>")
@role_required("teacher", "admin")
def delete_battle(battle_id):
    battle = battles_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Not found", 404)

    deleted, err = battles_service.delete_finished_battle(battle)
    if err == "battle_not_finished":
        return fail("Only finished battles can be deleted", 400)
    if not deleted:
        return fail("Delete failed", 400)

    return ok({"deleted": True, "battle_id": battle_id})


@battles_bp.get("/battles/<battle_id>/leaderboard")
@login_required
def leaderboard(battle_id):
    battle = battles_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Not found", 404)
    battles_service.tick_timeouts(battle)

    battle_points_expr = db.func.coalesce(db.func.sum(ScoreEvent.points_delta), 0)
    rows = (
        db.session.query(
            User.id,
            User.name,
            User.rating,
            battle_points_expr.label("battle_points"),
            User.win_streak,
            User.loss_streak,
        )
        .join(MatchParticipant, MatchParticipant.student_id == User.id)
        .join(Match, Match.id == MatchParticipant.match_id)
        .join(Room, Room.id == Match.room_id)
        .outerjoin(
            ScoreEvent,
            and_(
                ScoreEvent.match_id == Match.id,
                ScoreEvent.student_id == User.id,
            ),
        )
        .filter(Room.battle_id == battle.id, User.role == "student")
        .group_by(User.id, User.name, User.rating, User.win_streak, User.loss_streak)
        .order_by(battle_points_expr.desc(), User.rating.desc())
        .all()
    )
    return ok(
        {
            "battle_id": str(battle.id),
            "participants": [
                {
                    "user_id": str(row[0]),
                    "name": row[1],
                    "rating": row[2],
                    "season_points": int(row[3] or 0),
                    "battle_points": int(row[3] or 0),
                    "win_streak": row[4],
                    "loss_streak": row[5],
                    "is_online": presence_runtime.is_online(str(row[0])),
                }
                for row in rows
            ],
        }
    )


@battles_bp.get("/battles/<battle_id>/logs")
@role_required("teacher", "admin")
def battle_logs(battle_id):
    battle = battles_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Not found", 404)
    return ok(battles_service.list_battle_rooms_log(battle.id))


@battles_bp.get("/battles/<battle_id>/rooms/<room_id>/logs")
@role_required("teacher", "admin")
def battle_room_logs(battle_id, room_id):
    battle = battles_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Not found", 404)
    data = battles_service.get_battle_room_log_or_none(battle.id, room_id)
    if not data:
        return fail("Room not found in battle", 404)
    return ok(data)


@battles_bp.get("/battles/<battle_id>/submissions/<submission_id>")
@role_required("teacher", "admin")
def battle_submission(battle_id, submission_id):
    battle = battles_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Not found", 404)
    data = battles_service.get_battle_submission_or_none(battle.id, submission_id)
    if not data:
        return fail("Submission not found in battle", 404)
    return ok(data)


@battles_bp.post("/battles/<battle_id>/submissions/<submission_id>/recheck")
@role_required("teacher", "admin")
def battle_submission_recheck(battle_id, submission_id):
    battle = battles_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Not found", 404)

    callback_url = request.host_url.rstrip("/") + "/api/v1/integrations/geekpaste/callback"
    result, err = battles_service.recheck_battle_submission(
        battle_id=battle.id,
        submission_id=submission_id,
        callback_url=callback_url,
    )
    if err == "submission_not_found":
        return fail("Submission not found in battle", 404)
    if err == "checker_submit_failed":
        return fail("Failed to submit to checker", 502)

    return ok(
        {
            "submission_id": str(result["submission"].id),
            "status": "queued",
            "external": result["external"],
        },
        202,
    )


@battles_bp.get("/battles/<battle_id>/tasks")
@login_required
def battle_tasks(battle_id):
    battle = battles_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Not found", 404)
    return ok([task_out(t) for t in battles_service.list_battle_tasks(battle.id)])


@battles_bp.get("/battles/<battle_id>/task-packages")
@login_required
def battle_task_packages(battle_id):
    battle = battles_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Not found", 404)
    packages = battles_service.list_battle_task_packages(battle.id)
    return ok([task_package_out(p) for p in packages])


@battles_bp.post("/battles/<battle_id>/task-packages/<package_id>")
@role_required("teacher", "admin")
def add_task_package(battle_id, package_id):
    battle = battles_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Not found", 404)
    package, err = battles_service.add_task_package_to_battle(battle, package_id)
    if err == "package_not_found":
        return fail("Package not found", 404)
    return ok(task_package_out(package))


@battles_bp.delete("/battles/<battle_id>/task-packages/<package_id>")
@role_required("teacher", "admin")
def remove_task_package(battle_id, package_id):
    battle = battles_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Not found", 404)
    removed = battles_service.remove_task_package_from_battle(battle, package_id)
    return ok({"removed": removed})


@battles_bp.post("/battles/<battle_id>/tasks/<task_id>")
@role_required("teacher", "admin")
def add_task(battle_id, task_id):
    battle = battles_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Not found", 404)
    task, err = battles_service.add_task_to_battle(battle, task_id)
    if err == "task_not_found":
        return fail("Task not found", 404)
    return ok(task_out(task))


@battles_bp.delete("/battles/<battle_id>/tasks/<task_id>")
@role_required("teacher", "admin")
def remove_task(battle_id, task_id):
    battle = battles_service.get_battle_or_none(battle_id)
    if not battle:
        return fail("Not found", 404)
    removed = battles_service.remove_task_from_battle(battle, task_id)
    return ok({"removed": removed})
