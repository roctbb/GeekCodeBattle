import json
from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import Blueprint, request, session, current_app

from ..api.responses import ok, fail
from ..api.serializers import participant_out
from ..api.validators import VALID_LANGUAGES
from ..auth import login_required
from ..auth import current_user
from ..access import can_read_room, can_read_battle
from ..services import rooms_service, realtime_service
from ..services.scoring_service import (get_winner_info, try_finalize_after_submission,
    surrender_available_at, return_to_lobby, SURRENDER_SOLVE_BONUS)
from ..services.matchmaker_service import run_matchmaking
from ..services.test_visibility import task_tests, is_hidden, has_hidden_tests, hidden_test_feedback
from ..services.checker_feedback import (submission_test_counts, submission_verdict, feedback_payload,
                                         diagnostic_text, checker_error_type)
from ..extensions import db
from ..models import CodeRun, Match
from ..services.rooms_service import _as_utc


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


def _extract_visible_test_results(latest_submission, tests=None):
    results = []
    hidden = any(is_hidden(test) for test in tests or [])

    def _parse_status(item):
        if not isinstance(item, dict):
            return None
        if "ok" in item:
            return bool(item.get("ok"))
        if "passed" in item:
            return bool(item.get("passed"))
        if "status" in item:
            return str(item.get("status")).lower() in {"ok", "pass", "passed", "success"}
        return None

    def _parse_actual_output(item):
        if not isinstance(item, dict):
            return None
        for key in ("actual_output", "actual", "output", "stdout", "got", "received", "result", "answer", "user_output"):
            if key not in item:
                continue
            value = item.get(key)
            if value is None:
                continue
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            return str(value)
        return None

    if latest_submission and latest_submission.checker_comment_raw:
        try:
            parsed_comment = json.loads(latest_submission.checker_comment_raw)
            raw_visible = []
            visible_only = False
            if isinstance(parsed_comment, dict):
                visible_only = bool(parsed_comment.get("visible_tests"))
                raw_visible = (
                    parsed_comment.get("visible_tests")
                    or parsed_comment.get("tests")
                    or parsed_comment.get("details")
                    or []
                )
            elif isinstance(parsed_comment, list):
                raw_visible = parsed_comment

            if isinstance(raw_visible, list):
                for item in raw_visible:
                    if isinstance(item, dict):
                        results.append(
                            {
                                "passed": _parse_status(item),
                                "actual": _parse_actual_output(item),
                            }
                        )
                    else:
                        results.append({"passed": None, "actual": None})
                if hidden:
                    indices = [i for i, test in enumerate(tests) if not is_hidden(test)] if visible_only else list(range(len(tests)))
                    # Do not attach a hidden output to a public example if the
                    # checker returned an incomplete or ambiguous result list.
                    if len(results) != len(indices):
                        return []
                    aligned = [{} for _ in tests]
                    for index, result in zip(indices, results):
                        aligned[index] = result
                    results = aligned
        except Exception:
            results = []

    if (
        not results
        and not hidden
        and latest_submission
        and latest_submission.visible_tests_total is not None
        and latest_submission.visible_tests_passed is not None
    ):
        total = max(0, int(latest_submission.visible_tests_total))
        passed = max(0, min(total, int(latest_submission.visible_tests_passed)))
        results = [{"passed": True, "actual": None}] * passed + [{"passed": False, "actual": None}] * (total - passed)

    return results


def _extract_checker_feedback_text(latest_submission):
    if latest_submission is None:
        return None

    raw = latest_submission.checker_comment_raw
    if raw is None:
        return None
    diagnostics = diagnostic_text(feedback_payload(raw))
    if diagnostics:
        return diagnostics

    def _as_text(value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    try:
        parsed = json.loads(raw)
    except Exception:
        text = _as_text(raw)
        if not text:
            return None
        return text[:4000]

    if isinstance(parsed, str):
        text = _as_text(parsed)
        return text[:4000] if text else None

    if isinstance(parsed, dict):
        for key in (
            "comment",
            "message",
            "error",
            "stderr",
            "compile_error",
            "runtime_error",
            "traceback",
            "details",
        ):
            if key not in parsed:
                continue
            text = _as_text(parsed.get(key))
            if text:
                return text[:4000]
        if set(parsed) <= {'comment', 'details', 'tests_passed', 'tests_total', 'error_type'}:
            return None
        text = _as_text(parsed)
        return text[:4000] if text else None

    if isinstance(parsed, list):
        lines = []
        for item in parsed:
            if isinstance(item, dict):
                item_text = None
                for key in ("message", "error", "stderr", "comment", "output", "actual"):
                    if key in item:
                        item_text = _as_text(item.get(key))
                        if item_text:
                            break
                if not item_text:
                    item_text = _as_text(item)
            else:
                item_text = _as_text(item)
            if item_text:
                lines.append(item_text)
            if len(lines) >= 3:
                break
        if not lines:
            return None
        return "\n\n".join(lines)[:4000]

    text = _as_text(parsed)
    return text[:4000] if text else None


@rooms_bp.get("/rooms/<room_id>")
@login_required
def get_room(room_id):
    room = rooms_service.get_room_or_none(room_id)
    if not room:
        return fail("Not found", 404)
    if not can_read_room(current_user(), room):
        return fail("Forbidden", 403)

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

    tests = task_tests(task)
    visible_test_results = _extract_visible_test_results(latest_submission, tests)
    checker_feedback_text = (hidden_test_feedback(latest_submission) if has_hidden_tests(task)
                             else _extract_checker_feedback_text(latest_submission))

    public_tests = []
    if task and isinstance(task.config_json, dict):
        raw_tests = task.config_json.get("tests") or []
        if isinstance(raw_tests, list):
            for idx, item in enumerate(raw_tests):
                if not isinstance(item, dict) or is_hidden(item):
                    continue
                public_tests.append(
                    {
                        "input": str(item.get("input", "")),
                        "expected": str(item.get("expected", "")),
                        "passed": (
                            visible_test_results[idx].get("passed")
                            if idx < len(visible_test_results)
                            else None
                        ),
                        "actual": (
                            visible_test_results[idx].get("actual")
                            if idx < len(visible_test_results)
                            else None
                        ),
                    }
                )

    now = datetime.now(timezone.utc)
    active = bool(match and match.finished_at is None)
    preparing = bool(active and room.started_at and _as_utc(room.started_at) > now)
    me_row = next((p for p, _ in participants if str(p.student_id) == str(session["user_id"])), None)
    available_at = surrender_available_at(room, [p for p, _ in participants])
    round_info = {
        "started_at": _as_utc(room.started_at).isoformat() if room.started_at else None,
        "server_now": now.isoformat(),
        "is_active": active and not preparing,
        "is_preparing": preparing,
        "surrender_available_at": available_at.isoformat() if available_at else None,
        "can_surrender": bool(active and me_row and me_row.accepted_at is None
                              and me_row.surrendered_at is None and me_row.result_type != "loss"
                              and available_at and now >= available_at),
        "surrender_solve_bonus": SURRENDER_SOLVE_BONUS,
    }
    winner_info = {"winner_student_id": None, "winner_name": None}
    if active and participants:
        winner, _, _ = get_winner_info([p for p, _ in participants])
        if winner is not None:
            winner_user = next((u for p, u in participants if p.student_id == winner.student_id), None)
            winner_info = {"winner_student_id": str(winner.student_id),
                           "winner_name": winner_user.name if winner_user else None}

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
            if task and not preparing
            else None,
            "participants": [
                {
                    **participant_out(p),
                    "name": u.name,
                    "submissions_count": submission_counts.get(p.student_id, 0),
                }
                for p, u in participants
            ],
            "leader": winner_info,
            "round": round_info,
            "my_submission": {
                "id": str(latest_submission.id),
                "verdict": submission_verdict(latest_submission),
                "created_at": _as_utc(latest_submission.created_at).isoformat() if latest_submission.created_at else None,
                "checker_status": latest_submission.checker_status_raw,
                "checker_message": checker_feedback_text,
                **submission_test_counts(latest_submission),
                "source_code": latest_submission.source_code,
                "language": latest_submission.language,
            }
            if latest_submission
            else None,
        }
    )


@rooms_bp.get("/battles/<battle_id>/my-room")
@login_required
def my_room(battle_id):
    from ..services.battles_service import get_battle_or_none
    if not can_read_battle(current_user(), get_battle_or_none(battle_id)):
        return fail("Forbidden", 403)
    room = rooms_service.find_active_room_for_user(battle_id, session["user_id"])
    if not room:
        return ok({"room_id": None, "match_id": None})
    match = rooms_service.get_last_match(room.id)
    return ok({"room_id": str(room.id), "match_id": str(match.id) if match else None})


@rooms_bp.post("/rooms/<room_id>/submit")
@login_required
def submit(room_id):
    from ..services.scoring_service import lock_scoring
    lock_scoring()
    room = rooms_service.get_room_or_none(room_id)
    if not room:
        return fail("Not found", 404)

    data = request.get_json() or {}
    language = data.get("language")
    source_code = data.get("source_code", "")
    if not isinstance(source_code, str) or not source_code.strip():
        return fail("source_code must be non-empty text", 400)
    if language not in VALID_LANGUAGES:
        return fail("language must be one of: python, cpp", 400)
    if len(source_code.encode("utf-8")) > 256 * 1024:
        return fail("source_code is too large", 413)

    match = rooms_service.get_last_match(room.id)
    if match:
        # Serialize submissions for a room before inspecting pending attempts.
        from ..models import Match
        match = Match.query.filter_by(id=match.id).with_for_update().populate_existing().first()
    if not match or match.finished_at is not None:
        return fail("No active match", 400)
    participant = rooms_service.get_match_participant(match.id, session["user_id"])
    if not participant:
        return fail("Not a participant of this match", 403)
    if room.started_at and _as_utc(room.started_at) > datetime.now(timezone.utc):
        return fail("Round has not started yet", 409)
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
        if not rooms_service.mark_submission_checker_error(submission, exc):
            return ok({"submission_id": str(submission.id), "status": submission.verdict}, 202)
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


def _practice_timeout():
    return max(1, int(current_app.config.get("SUBMISSION_CHECK_TIMEOUT_SECONDS", 180) or 180))


def _practice_message(raw, depth=0):
    if raw is None or depth > 6:
        return None
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            return raw.strip()[:4000] or None
        if parsed != raw:
            return _practice_message(parsed, depth + 1)
        return raw.strip()[:4000] or None
    if isinstance(raw, dict):
        for key in ("comment", "message", "error", "stderr", "compile_error", "runtime_error", "traceback", "details", "tests", "visible_tests"):
            message = _practice_message(raw.get(key), depth + 1)
            if message:
                return message
    if isinstance(raw, list):
        messages = [_practice_message(item, depth + 1) for item in raw[:3]]
        return "\n\n".join(message for message in messages if message)[:4000] or None
    return None


def _run_out(run):
    from types import SimpleNamespace
    feedback = SimpleNamespace(checker_comment_raw=run.checker_comment_raw,
                               visible_tests_total=None, visible_tests_passed=None)
    results = _extract_visible_test_results(feedback, run.tests)
    payload = feedback_payload(run.checker_comment_raw)
    message = diagnostic_text(payload) or _practice_message(run.checker_comment_raw)
    error_type = checker_error_type(payload)
    if not message and run.verdict == "internal_error":
        message = "Не удалось выполнить код. Повторите запуск."
    return {"id": str(run.id), "kind": run.kind, "verdict": run.verdict, "created_at": _as_utc(run.created_at).isoformat(), "timeout_seconds": _practice_timeout(),
            "language": run.language, "source_code": run.source_code,
            "message": message,
            "error_type": error_type,
            **(submission_test_counts(run) if run.kind == 'examples' else {}),
            "tests": [{"input": t["input"], "expected": t.get("expected") if run.kind == "examples" else None,
                       "actual": results[i].get("actual") if i < len(results) else None,
                       "passed": results[i].get("passed") if i < len(results) and run.kind == "examples" else None}
                      for i, t in enumerate(run.tests)]}


@rooms_bp.post("/rooms/<room_id>/runs")
@login_required
def create_run(room_id):
    try:
        room = rooms_service.get_room_or_none(room_id)
    except (ValueError, TypeError, AttributeError):
        return fail("Not found", 404)
    if not room:
        return fail("Not found", 404)
    match = rooms_service.get_last_match(room.id)
    participant = rooms_service.get_match_participant(match.id, session["user_id"]) if match else None
    if not match or not participant:
        return fail("Forbidden", 403)
    match = Match.query.filter_by(id=match.id).with_for_update().populate_existing().first()
    now = datetime.now(timezone.utc)
    if match.finished_at:
        return fail("Round is already finished", 409)
    if participant.accepted_at is not None or participant.result_type == "loss":
        return fail("Round is already finished", 409)
    if room.started_at and _as_utc(room.started_at) > now:
        return fail("Round has not started yet", 409)
    data = request.get_json() or {}
    if not isinstance(data, dict):
        return fail("Run must be an object", 400)
    code, language, kind = data.get("source_code"), data.get("language"), data.get("kind", "examples")
    if (not isinstance(code, str) or not code.strip() or not isinstance(language, str)
            or language not in VALID_LANGUAGES or not isinstance(kind, str) or kind not in {"examples", "custom"}):
        return fail("Invalid run: code, language and kind are required", 400)
    if len(code.encode("utf-8")) > 256 * 1024:
        return fail("source_code is too large", 413)
    task = rooms_service.get_task_for_match(match)
    if kind == "custom":
        stdin = data.get("input", "")
        if not isinstance(stdin, str) or len(stdin.encode("utf-8")) > 64 * 1024:
            return fail("Input must be text up to 64 KiB", 400)
        tests = [{"input": stdin, "expected": ""}]
    else:
        tests = [{"input": str(t.get("input", "")), "expected": str(t.get("expected", ""))}
                 for t in task_tests(task) if isinstance(t, dict) and not is_hidden(t)]
        if not tests:
            return fail("No public examples available", 400)
    runs = CodeRun.query.filter_by(match_id=match.id, student_id=current_user().id)
    latest = runs.order_by(CodeRun.created_at.desc()).with_for_update().populate_existing().first()
    if latest and latest.verdict == "queued":
        if (now - _as_utc(latest.created_at)).total_seconds() < _practice_timeout():
            return fail("Previous run is still being checked", 409, details={"run_id": str(latest.id)})
        latest.verdict = "internal_error"
        latest.checker_comment_raw = "Проверяющая система не ответила. Повторите запуск."
    if runs.count() >= 100:
        return fail("Practice limit reached: 100 runs per round", 429)
    run = CodeRun(match_id=match.id, student_id=current_user().id, language=language,
                  source_code=code, kind=kind, tests=tests)
    db.session.add(run)
    db.session.commit()
    try:
        # Only explicitly public examples or the user's input reach this checker job.
        external = rooms_service.submit_for_check(callback_url=_callback_base_url() + "/api/v1/integrations/geekpaste/run-callback",
            callback_id=str(run.id), code=code, lang=language, task_text="", check_type="tests", check_config={"tests": tests})
        run.external_run_id = external.get("job_id")
        db.session.commit()
    except Exception:
        CodeRun.query.filter_by(id=run.id, verdict="queued").update({"verdict": "internal_error",
            "checker_comment_raw": "Не удалось запустить код. Повторите попытку."}, synchronize_session=False)
        db.session.commit()
        db.session.refresh(run)
    return ok(_run_out(run), 202)


@rooms_bp.get("/rooms/<room_id>/runs/<run_id>")
@login_required
def get_run(room_id, run_id):
    from ..utils import as_uuid
    try:
        run = CodeRun.query.filter_by(id=as_uuid(run_id)).with_for_update().populate_existing().first()
    except (ValueError, TypeError, AttributeError):
        return fail("Not found", 404)
    if not run or str(run.student_id) != str(session["user_id"]):
        return fail("Not found", 404)
    match = db.session.get(Match, run.match_id)
    if not match or str(match.room_id) != room_id:
        return fail("Not found", 404)
    if run.verdict == "queued" and (datetime.now(timezone.utc) - _as_utc(run.created_at)).total_seconds() >= _practice_timeout():
        run.verdict = "internal_error"
        run.checker_comment_raw = "Проверяющая система не ответила. Повторите запуск."
        db.session.commit()
    return ok(_run_out(run))


@rooms_bp.post("/rooms/<room_id>/surrender")
@login_required
def surrender(room_id):
    from ..services.scoring_service import lock_scoring
    lock_scoring()
    room = rooms_service.get_room_or_none(room_id)
    if not room:
        return fail("Not found", 404)

    match = rooms_service.get_last_match(room.id)
    if not match or match.finished_at is not None:
        return fail("No active match", 400)

    # The same ledger lock also serializes checker acceptance and surrender.
    me = rooms_service.get_match_participant(match.id, session["user_id"])
    if not me:
        return fail("Not a participant of this match", 403)
    if me.surrendered_at is not None or me.result_type == "loss":
        return ok({"status": "already_surrendered"})
    if me.accepted_at is not None:
        return fail("Accepted participant cannot surrender", 409)
    available_at = surrender_available_at(room, rooms_service.list_match_participants(match.id))
    now = datetime.now(timezone.utc)
    if available_at is None or now < available_at:
        return fail("Surrender is available after 10 minutes", 409)

    me.surrendered_at = now
    me.result_type = "loss"
    return_to_lobby(room.battle_id, [me], match.id)
    db.session.commit()
    realtime_service.emit_queue_updated(room.battle_id, {"battle_id": str(room.battle_id)})

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
