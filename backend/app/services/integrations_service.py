import hashlib
import json
import time

import jwt
import redis
from flask import current_app

from ..extensions import db
from ..models import Submission, MatchParticipant, Match, Room, QueueEntry, Battle
from ..utils import as_uuid
from .scoring_service import try_finalize_after_submission, award_instant_winner_points
from .matchmaker_service import run_matchmaking
from .realtime_service import emit_submission_verdict, emit_round_finished, emit_leaderboard_updated, emit_match_found, emit_queue_updated


def _to_int_or_none(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def redis_client():
    return redis.from_url(current_app.config["REDIS_URL"], decode_responses=True)


def verify_callback_auth(auth_header):
    if not current_app.config["GEEKPASTE_CALLBACK_REQUIRE_AUTH"]:
        return None
    if not auth_header.startswith("Bearer "):
        return "unauthorized"
    token = auth_header[7:]
    try:
        payload = jwt.decode(token, current_app.config["JWT_SECRET"], algorithms=["HS256"])
    except Exception:
        return "unauthorized"

    if payload.get("service") != current_app.config["GEEKPASTE_CALLBACK_EXPECTED_SERVICE"]:
        return "forbidden"

    iat = payload.get("iat")
    now = int(time.time())
    if not isinstance(iat, int):
        return "unauthorized"
    if iat > now + 30:
        return "unauthorized"
    if now - iat > current_app.config["GEEKPASTE_CALLBACK_MAX_AGE_SECONDS"]:
        return "expired"
    return None


def dedupe_key(payload, callback_id):
    job_id = payload.get("job_id")
    if job_id:
        return f"geekcodebattle:callback:{callback_id}:{job_id}"
    payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return f"geekcodebattle:callback:{callback_id}:hash:{payload_hash}"


def callback_is_duplicate(payload, callback_id):
    key = dedupe_key(payload, callback_id)
    try:
        return redis_client().exists(key) == 1
    except Exception:
        return False


def mark_callback_processed(payload, callback_id):
    key = dedupe_key(payload, callback_id)
    try:
        redis_client().set(key, "1", ex=current_app.config["GEEKPASTE_CALLBACK_DEDUP_TTL_SECONDS"])
    except Exception:
        pass


def apply_checker_result(payload):
    callback_id = payload.get("callback_id")
    submission = db.session.get(Submission, as_uuid(callback_id))
    if not submission:
        return None
    if submission.verdict != "queued":
        current_app.logger.info(
            "checker_callback_ignored callback_id=%s current_verdict=%s",
            callback_id,
            submission.verdict,
        )
        return submission

    status = payload.get("status", "error")
    points = payload.get("points", 0) or 0
    max_points = payload.get("max_points", 1) or 1
    progress = max(0.0, min(1.0, float(points) / float(max_points)))

    submission.checker_status_raw = status

    comment_raw = payload.get("comment")
    details_raw = payload.get("details")
    if isinstance(details_raw, list):
        # Preserve per-test details from checker callback for UI rendering.
        submission.checker_comment_raw = json.dumps(
            {
                "comment": comment_raw,
                "details": details_raw,
            },
            ensure_ascii=False,
        )
    elif isinstance(comment_raw, (dict, list)):
        submission.checker_comment_raw = json.dumps(comment_raw, ensure_ascii=False)
    elif comment_raw is None:
        submission.checker_comment_raw = None
    else:
        submission.checker_comment_raw = str(comment_raw)

    submission.callback_received_at = db.func.now()
    submission.verdict = "accepted" if status == "success" and progress >= 1.0 else ("wrong_answer" if status == "success" else "internal_error")
    submission.progress_value = progress
    submission.visible_tests_passed = _to_int_or_none(payload.get("visible_tests_passed"))
    submission.visible_tests_total = _to_int_or_none(payload.get("visible_tests_total"))
    submission.hidden_tests_passed = _to_int_or_none(payload.get("hidden_tests_passed"))
    submission.hidden_tests_total = _to_int_or_none(payload.get("hidden_tests_total"))

    match = db.session.get(Match, submission.match_id)
    room = db.session.get(Room, match.room_id) if match else None
    match_is_active = bool(match and match.finished_at is None)
    participant = None
    became_accepted = False
    if match_is_active:
        participant = MatchParticipant.query.filter_by(match_id=submission.match_id, student_id=submission.student_id).first()
        if participant:
            participant.progress = max(float(participant.progress or 0), progress)
            if submission.verdict == "accepted" and participant.accepted_at is None:
                participant.accepted_at = db.func.now()
                became_accepted = True

    db.session.commit()
    emit_submission_verdict(
        submission.match_id,
        submission.student_id,
        submission.verdict,
        progress,
        battle_id=(room.battle_id if room else None),
        visible_tests_passed=submission.visible_tests_passed,
        visible_tests_total=submission.visible_tests_total,
    )

    if match_is_active:
        instant_points_delta = 0
        if became_accepted and participant:
            instant_points_delta = int(award_instant_winner_points(match, participant.student_id) or 0)
            if instant_points_delta > 0 and room:
                emit_leaderboard_updated(room.battle_id)

        finalized = try_finalize_after_submission(match)
        if finalized:
            db.session.refresh(match)
        if room:
            if finalized:
                emit_round_finished(match.id, match.finished_by or "accepted")
                emit_leaderboard_updated(room.battle_id)
                created_rooms = run_matchmaking(room.battle_id)
                for room_info in created_rooms:
                    emit_match_found(room_info)
            elif became_accepted:
                battle = db.session.get(Battle, room.battle_id)
                if battle and battle.status == "running":
                    queue_entry = QueueEntry.query.filter_by(battle_id=battle.id, user_id=submission.student_id).first()
                    changed = False
                    if not queue_entry:
                        db.session.add(QueueEntry(battle_id=battle.id, user_id=submission.student_id, is_ready=False))
                        changed = True
                    elif queue_entry.is_ready:
                        queue_entry.is_ready = False
                        changed = True
                    if changed:
                        db.session.commit()
                        emit_queue_updated(battle.id, {"battle_id": str(battle.id)})
    return submission
