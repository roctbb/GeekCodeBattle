import json
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

from flask import Blueprint, request, session, current_app

from ..api.responses import ok, fail
from ..api.serializers import participant_out
from ..api.validators import VALID_LANGUAGES
from ..auth import login_required
from ..services import rooms_service, realtime_service
from ..services.scoring_service import get_winner_info, try_finalize_after_submission
from ..services.matchmaker_service import run_matchmaking
from ..extensions import db


rooms_bp = Blueprint("rooms", __name__, url_prefix="/api/v1")


def _emit_finalize_side_effects(match, battle_id):
    realtime_service.emit_round_finished(match.id, match.finished_by or "accepted")
    realtime_service.emit_leaderboard_updated(battle_id)
    created_rooms = run_matchmaking(battle_id)
    for room_info in created_rooms:
        realtime_service.emit_match_found(room_info)


def _callback_base_url():
    explicit_backend_url = str(current_app.config.get("BACKEND_URL") or "").strip()
    if explicit_backend_url:
        parsed = urlparse(explicit_backend_url)
        host = (parsed.hostname or "").strip().lower()
        # External checker cannot call back to loopback addresses.
        if host not in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
            return explicit_backend_url.rstrip("/")
        current_app.logger.warning(
            "callback_base_url_ignored_localhost backend_url=%s host_url=%s",
            explicit_backend_url,
            request.host_url,
        )
        return request.host_url.rstrip("/")
    return request.host_url.rstrip("/")


@rooms_bp.get("/rooms/<room_id>")
@login_required
def get_room(room_id):
    room = rooms_service.get_room_or_none(room_id)
    if not room:
        return fail("Not found", 404)

    match = rooms_service.get_last_match(room.id)
    if match and match.finished_at is None:
        rooms_service.expire_stale_submissions(match.id, battle_id=room.battle_id)
        finalized = try_finalize_after_submission(match)
        if finalized:
            db.session.refresh(match)
            _emit_finalize_side_effects(match, room.battle_id)

    participants = rooms_service.list_match_participants_with_users(match.id) if match else []
    submission_counts = rooms_service.get_submission_counts_for_match(match.id) if match else {}
    task = rooms_service.get_task_for_match(match)
    latest_submission = None
    if match:
        latest_submission = rooms_service.get_latest_submission(match.id, session["user_id"])

    visible_test_statuses = []
    if latest_submission and latest_submission.checker_comment_raw:
        try:
            parsed_comment = json.loads(latest_submission.checker_comment_raw)
            if isinstance(parsed_comment, dict):
                raw_visible = (
                    parsed_comment.get("visible_tests")
                    or parsed_comment.get("tests")
                    or parsed_comment.get("details")
                    or []
                )
                if isinstance(raw_visible, list):
                    for item in raw_visible:
                        if not isinstance(item, dict):
                            visible_test_statuses.append(None)
                            continue
                        if "ok" in item:
                            visible_test_statuses.append(bool(item.get("ok")))
                        elif "passed" in item:
                            visible_test_statuses.append(bool(item.get("passed")))
                        elif "status" in item:
                            visible_test_statuses.append(str(item.get("status")).lower() in {"ok", "pass", "passed", "success"})
                        else:
                            visible_test_statuses.append(None)
        except Exception:
            visible_test_statuses = []

    if (
        not visible_test_statuses
        and latest_submission
        and latest_submission.visible_tests_total is not None
        and latest_submission.visible_tests_passed is not None
    ):
        total = max(0, int(latest_submission.visible_tests_total))
        passed = max(0, min(total, int(latest_submission.visible_tests_passed)))
        visible_test_statuses = [True] * passed + [False] * (total - passed)

    public_tests = []
    if task and isinstance(task.config_json, dict):
        raw_tests = task.config_json.get("tests") or []
        if isinstance(raw_tests, list):
            for idx, item in enumerate(raw_tests):
                if not isinstance(item, dict):
                    continue
                public_tests.append(
                    {
                        "input": str(item.get("input", "")),
                        "expected": str(item.get("expected", "")),
                        "passed": visible_test_statuses[idx] if idx < len(visible_test_statuses) else None,
                    }
                )

    round_info = {"started_at": None, "deadline_at": None, "seconds_left": 0, "is_active": False, "duration_minutes": int(current_app.config.get("ROUND_DURATION_MINUTES", 20))}
    if room.started_at is not None and match and match.finished_at is None:
        round_started_at = room.started_at
        if round_started_at.tzinfo is None:
            round_started_at = round_started_at.replace(tzinfo=timezone.utc)
        round_deadline = round_started_at + timedelta(minutes=round_info["duration_minutes"])
        round_seconds_left = max(0, int((round_deadline - datetime.now(timezone.utc)).total_seconds()))
        round_info = {
            "started_at": round_started_at.isoformat(),
            "deadline_at": round_deadline.isoformat(),
            "seconds_left": round_seconds_left,
            "is_active": round_seconds_left > 0,
            "duration_minutes": round_info["duration_minutes"],
        }

    winner_info = {"winner_student_id": None, "winner_name": None, "deadline_at": None, "seconds_left": 0, "is_active": False, "can_surrender": False}
    if match and match.finished_at is None and participants:
        participant_rows = [p for p, _ in participants]
        winner, winner_ts, _ = get_winner_info(participant_rows)
        if winner is not None and winner_ts is not None:
            deadline = winner_ts + timedelta(minutes=int(current_app.config.get("POST_WIN_GRACE_MINUTES", 5)))
            now = datetime.now(timezone.utc)
            seconds_left = max(0, int((deadline - now).total_seconds()))
            me_row = next((p for p, _ in participants if str(p.student_id) == str(session["user_id"])), None)
            can_surrender = bool(
                me_row
                and str(me_row.student_id) != str(winner.student_id)
                and me_row.result_type != "loss"
            )
            winner_user = next((u for p, u in participants if str(p.student_id) == str(winner.student_id)), None)
            winner_info = {
                "winner_student_id": str(winner.student_id),
                "winner_name": winner_user.name if winner_user else None,
                "deadline_at": deadline.isoformat(),
                "seconds_left": seconds_left,
                "is_active": seconds_left > 0,
                "can_surrender": can_surrender and seconds_left > 0,
            }

    return ok(
        {
            "id": str(room.id),
            "battle_id": str(room.battle_id),
            "status": room.status,
            "match_id": str(match.id) if match else None,
            "task": {
                "id": str(task.id),
                "title": task.title,
                "statement_md": task.statement_md,
                "check_type": task.check_type,
                "difficulty": task.difficulty,
                "public_tests": public_tests,
            }
            if task
            else None,
            "participants": [
                {
                    **participant_out(p),
                    "name": u.name,
                    "submissions_count": submission_counts.get(p.student_id, 0),
                }
                for p, u in participants
            ],
            "grace": winner_info,
            "round": round_info,
            "my_submission": {
                "id": str(latest_submission.id),
                "verdict": latest_submission.verdict,
                "created_at": latest_submission.created_at.isoformat() if latest_submission.created_at else None,
            }
            if latest_submission
            else None,
        }
    )


@rooms_bp.get("/battles/<battle_id>/my-room")
@login_required
def my_room(battle_id):
    room = rooms_service.find_active_room_for_user(battle_id, session["user_id"])
    if not room:
        return ok({"room_id": None, "match_id": None})
    match = rooms_service.get_last_match(room.id)
    return ok({"room_id": str(room.id), "match_id": str(match.id) if match else None})


@rooms_bp.post("/rooms/<room_id>/submit")
@login_required
def submit(room_id):
    room = rooms_service.get_room_or_none(room_id)
    if not room:
        return fail("Not found", 404)

    data = request.get_json() or {}
    language = data.get("language")
    source_code = data.get("source_code", "")
    if language not in VALID_LANGUAGES:
        return fail("language must be one of: python, cpp", 400)
    if len(source_code.encode("utf-8")) > 256 * 1024:
        return fail("source_code is too large", 413)

    match = rooms_service.get_last_match(room.id)
    if not match or match.finished_at is not None:
        return fail("No active match", 400)
    participant = rooms_service.get_match_participant(match.id, session["user_id"])
    if not participant:
        return fail("Not a participant of this match", 403)
    if participant and (participant.accepted_at is not None or participant.result_type == "loss"):
        return fail("Round is already finished for you", 409)
    latest_submission = rooms_service.get_latest_submission(match.id, session["user_id"])
    if latest_submission and latest_submission.verdict == "queued":
        return fail("Previous submission is still being checked", 409)
    if try_finalize_after_submission(match):
        db.session.refresh(match)
        _emit_finalize_side_effects(match, room.battle_id)
        return fail("Round is already finished", 409)

    submission = rooms_service.create_submission(
        match_id=match.id,
        student_id=session["user_id"],
        language=language,
        source_code=source_code,
    )
    realtime_service.emit_submission_queued(match.id, submission.student_id, battle_id=room.battle_id)

    task = rooms_service.get_task_for_match(match)
    callback_url = _callback_base_url() + "/api/v1/integrations/geekpaste/callback"
    try:
        external = rooms_service.submit_to_checker(
            submission=submission,
            callback_url=callback_url,
            task_text=(task.statement_md if task else ""),
            check_type=(task.check_type if task else "tests"),
            check_config=(task.config_json if task else {}),
        )
    except Exception as exc:
        rooms_service.mark_submission_checker_error(submission, exc)
        realtime_service.emit_submission_verdict(
            match.id,
            submission.student_id,
            "internal_error",
            0,
            battle_id=room.battle_id,
            visible_tests_passed=0,
            visible_tests_total=None,
        )
        return fail("Failed to submit to checker", 502, details=str(exc))

    return ok({"submission_id": str(submission.id), "status": "queued", "external": external}, 202)


@rooms_bp.post("/rooms/<room_id>/surrender")
@login_required
def surrender(room_id):
    room = rooms_service.get_room_or_none(room_id)
    if not room:
        return fail("Not found", 404)

    match = rooms_service.get_last_match(room.id)
    if not match or match.finished_at is not None:
        return fail("No active match", 400)

    participants = rooms_service.list_match_participants(match.id)
    winner, _, _ = get_winner_info(participants)
    if winner is None:
        return fail("Cannot surrender before first winner", 400)
    if try_finalize_after_submission(match):
        db.session.refresh(match)
        _emit_finalize_side_effects(match, room.battle_id)
        return fail("Round is already finished", 409)

    me = rooms_service.get_match_participant(match.id, session["user_id"])
    if not me:
        return fail("Not a participant of this match", 403)
    if str(me.student_id) == str(winner.student_id):
        return fail("Winner cannot surrender", 400)
    if me.result_type == "loss":
        return ok({"status": "already_surrendered"})

    me.result_type = "loss"
    db.session.commit()

    realtime_service.emit_submission_verdict(
        match.id,
        me.student_id,
        "surrendered",
        float(me.progress or 0),
        battle_id=room.battle_id,
    )

    finalized = try_finalize_after_submission(match)
    if finalized:
        db.session.refresh(match)
        _emit_finalize_side_effects(match, room.battle_id)

    return ok({"status": "surrendered"})
