from datetime import datetime, timedelta, timezone

from flask import current_app

from ..extensions import db
from ..models import Room, Match, MatchParticipant, Submission, Task, User
from ..utils import as_uuid
from .checker import submit_for_check
from .realtime_service import emit_submission_verdict


def get_room_or_none(room_id):
    return db.session.get(Room, as_uuid(room_id))


def get_last_match(room_id):
    return Match.query.filter_by(room_id=as_uuid(room_id)).order_by(Match.created_at.desc()).first()


def find_active_room_for_user(battle_id, user_id):
    return (
        db.session.query(Room)
        .join(Match, Match.room_id == Room.id)
        .join(MatchParticipant, MatchParticipant.match_id == Match.id)
        .filter(
            Room.battle_id == as_uuid(battle_id),
            MatchParticipant.student_id == as_uuid(user_id),
            Match.finished_at.is_(None),
            MatchParticipant.accepted_at.is_(None),
            db.or_(MatchParticipant.result_type.is_(None), MatchParticipant.result_type != "loss"),
        )
        .order_by(Room.created_at.desc())
        .first()
    )


def list_match_participants(match_id):
    return MatchParticipant.query.filter_by(match_id=as_uuid(match_id)).all()


def list_match_participants_with_users(match_id):
    return (
        db.session.query(MatchParticipant, User)
        .join(User, User.id == MatchParticipant.student_id)
        .filter(MatchParticipant.match_id == as_uuid(match_id))
        .all()
    )


def get_submission_counts_for_match(match_id):
    rows = (
        db.session.query(Submission.student_id, db.func.count(Submission.id))
        .filter(Submission.match_id == as_uuid(match_id))
        .group_by(Submission.student_id)
        .all()
    )
    return {student_id: int(count or 0) for student_id, count in rows}


def get_match_participant(match_id, student_id):
    return MatchParticipant.query.filter_by(match_id=as_uuid(match_id), student_id=as_uuid(student_id)).first()


def get_latest_submission(match_id, student_id):
    return (
        Submission.query
        .filter_by(match_id=as_uuid(match_id), student_id=as_uuid(student_id))
        .order_by(Submission.created_at.desc())
        .first()
    )


def get_task_for_match(match):
    if not match:
        return None
    return db.session.get(Task, match.task_id)


def create_submission(*, match_id, student_id, language, source_code):
    submission = Submission(
        match_id=as_uuid(match_id),
        student_id=as_uuid(student_id),
        language=language,
        source_code=source_code,
        verdict="queued",
    )
    db.session.add(submission)
    db.session.commit()
    return submission


def submit_to_checker(*, submission, callback_url, task_text="", check_type="tests", check_config=None):
    result = submit_for_check(
        callback_url=callback_url,
        callback_id=str(submission.id),
        code=submission.source_code,
        lang=submission.language,
        task_text=task_text,
        check_type=check_type,
        check_config=check_config or {},
    )
    submission.external_run_id = result.get("job_id")
    db.session.commit()
    return result


def mark_submission_checker_error(submission, details):
    submission.verdict = "internal_error"
    submission.checker_comment_raw = str(details)
    db.session.commit()


def _as_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def expire_stale_submissions(match_id, battle_id=None):
    timeout_seconds = int(current_app.config.get("SUBMISSION_CHECK_TIMEOUT_SECONDS", 180) or 0)
    if timeout_seconds <= 0:
        return 0

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=timeout_seconds)

    queued = (
        Submission.query
        .filter_by(match_id=as_uuid(match_id), verdict="queued")
        .all()
    )
    expired = []
    for submission in queued:
        created_at = _as_utc(submission.created_at)
        if created_at is None or created_at > cutoff:
            continue
        submission.verdict = "wrong_answer"
        submission.progress_value = 0
        submission.checker_status_raw = "timeout"
        submission.checker_comment_raw = (
            f"Checker timeout: no result received within {timeout_seconds} seconds"
        )
        submission.callback_received_at = now
        expired.append(submission)

    if not expired:
        return 0

    db.session.commit()
    for submission in expired:
        emit_submission_verdict(
            submission.match_id,
            submission.student_id,
            submission.verdict,
            0,
            battle_id=battle_id,
            visible_tests_passed=0,
            visible_tests_total=submission.visible_tests_total,
        )
    return len(expired)
