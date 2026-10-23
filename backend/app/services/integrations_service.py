import hashlib
import json
import time
from datetime import datetime, timezone

import jwt
import redis
from flask import current_app

from ..extensions import db
from ..models import Submission, MatchParticipant, Match, Room, QueueEntry, Battle
from ..utils import as_uuid
from .scoring_service import try_finalize_after_submission, award_instant_winner_points
from .matchmaker_service import run_matchmaking
from .realtime_service import emit_submission_verdict, emit_round_finished, emit_leaderboard_updated, emit_match_found, emit_queue_updated
from .checker_feedback import checker_verdict, checker_error_type, checker_test_counts, feedback_payload
from .test_visibility import task_tests


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


def checker_feedback_raw(payload):
    """Keep structured feedback when the checker omits top-level details."""
    comment = payload.get("comment")
    details = payload.get("details")
    if any(key in payload for key in ('tests_passed', 'tests_total', 'error_type')):
        feedback = feedback_payload(comment)
        if isinstance(details, list) and details:
            feedback['details'] = details
        feedback.update({key: payload[key] for key in (
            'tests_passed', 'tests_total', 'error_type') if key in payload})
        return json.dumps(feedback, ensure_ascii=False)
    if isinstance(details, list) and details:
        return json.dumps({"comment": comment, "details": details}, ensure_ascii=False)
    if isinstance(comment, (dict, list)):
        return json.dumps(comment, ensure_ascii=False)
    return str(comment) if comment is not None else None


def callback_can_update(submission, payload):
    """Only a matching job can recover a timeout; final verdicts stay immutable."""
    callback_id = payload.get('callback_id')
    late_timeout = submission.verdict == 'internal_error' and submission.checker_status_raw == 'timeout'
    job_id = payload.get('job_id')
    if ((submission.external_run_id and job_id and job_id != submission.external_run_id)
            or (late_timeout and (not submission.external_run_id or job_id != submission.external_run_id))):
        current_app.logger.warning(
            'checker_callback_job_mismatch callback_id=%s job_id=%s expected_job_id=%s',
            callback_id, job_id, submission.external_run_id,
        )
        return False
    if submission.verdict != "queued" and not late_timeout:
        current_app.logger.info(
            "checker_callback_ignored callback_id=%s current_verdict=%s",
            callback_id,
            submission.verdict,
        )
        return False

    if late_timeout:
        current_app.logger.info('checker_callback_after_timeout callback_id=%s job_id=%s', callback_id, job_id)
    return True


def apply_checker_result(payload):
    from .scoring_service import lock_scoring
    lock_scoring()
    callback_id = payload.get("callback_id")
    submission = Submission.query.filter_by(id=as_uuid(callback_id)).with_for_update().populate_existing().first()
    if not submission:
        return None
    if not callback_can_update(submission, payload):
        return submission

    status = payload.get("status", "error")
    points = payload.get("points", 0) or 0
    max_points = payload.get("max_points", 1) or 1
    progress = max(0.0, min(1.0, float(points) / float(max_points)))

    submission.checker_status_raw = status

    match = db.session.get(Match, submission.match_id)
    from ..models import Task
    task = db.session.get(Task, match.task_id) if match else None
    tests_passed, tests_total = checker_test_counts(
        payload, check_type=task.check_type if task else None, tests=task_tests(task))
    submission.checker_comment_raw = checker_feedback_raw({
        **payload, 'tests_passed': tests_passed, 'tests_total': tests_total,
        'error_type': checker_error_type(payload),
    })

    submission.callback_received_at = db.func.now()
    submission.verdict = checker_verdict(payload, progress)
    submission.progress_value = progress
    submission.visible_tests_passed = _to_int_or_none(payload.get("visible_tests_passed"))
    submission.visible_tests_total = _to_int_or_none(payload.get("visible_tests_total"))
    submission.hidden_tests_passed = _to_int_or_none(payload.get("hidden_tests_passed"))
    submission.hidden_tests_total = _to_int_or_none(payload.get("hidden_tests_total"))

    room = db.session.get(Room, match.room_id) if match else None
    match_is_active = bool(match and match.finished_at is None)
    participant = None
    became_accepted = False
    if match_is_active:
        participant = MatchParticipant.query.filter_by(match_id=submission.match_id, student_id=submission.student_id).first()
        if participant and participant.surrendered_at is None and participant.result_type != "loss":
            participant.progress = max(float(participant.progress or 0), progress)
            if submission.verdict == "accepted" and participant.accepted_at is None:
                participant.accepted_at = datetime.now(timezone.utc)
                became_accepted = True

    db.session.commit()
    emit_submission_verdict(
        submission.match_id,
        submission.student_id,
        "surrendered" if participant and participant.surrendered_at else submission.verdict,
        progress,
        battle_id=(room.battle_id if room else None),
        visible_tests_passed=submission.visible_tests_passed,
        visible_tests_total=submission.visible_tests_total,
        tests_passed=tests_passed,
        tests_total=tests_total,
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
