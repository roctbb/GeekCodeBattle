from flask import Blueprint, request, current_app

from ..api.responses import ok, fail
from ..services import integrations_service
from ..extensions import db
from ..models import CodeRun
from ..utils import as_uuid
from ..services.checker_feedback import checker_error_type, checker_test_counts


integrations_bp = Blueprint("integrations", __name__, url_prefix="/api/v1/integrations")


@integrations_bp.post("/geekpaste/run-callback")
def code_run_callback():
    error = integrations_service.verify_callback_auth(request.headers.get("Authorization", ""))
    if error:
        return fail("Callback authentication failed", 403 if error == "forbidden" else 401)
    payload = request.get_json() or {}
    if not isinstance(payload, dict) or not payload.get("callback_id"):
        return fail("Missing callback_id", 400)
    try:
        run_id = as_uuid(payload["callback_id"])
    except (ValueError, TypeError, AttributeError):
        return fail("Invalid callback_id", 400)
    run = CodeRun.query.filter_by(id=run_id).with_for_update().populate_existing().first()
    if not run:
        return fail("Run not found", 404)
    if not integrations_service.callback_can_update(run, payload):
        return ok({"duplicate": True})
    run.checker_status_raw = str(payload.get("status", "error"))
    run.verdict = "completed" if run.checker_status_raw == "success" else "internal_error"
    error_type = checker_error_type(payload)
    if error_type:
        run.verdict = error_type
    tests_passed, tests_total = checker_test_counts(payload, check_type='tests', tests=run.tests)
    run.checker_comment_raw = integrations_service.checker_feedback_raw({
        **payload, 'error_type': error_type, 'tests_passed': tests_passed, 'tests_total': tests_total,
    })
    db.session.commit()
    return ok()


@integrations_bp.post("/geekpaste/callback")
def geekpaste_callback():
    auth_error = integrations_service.verify_callback_auth(request.headers.get("Authorization", ""))
    if auth_error == "unauthorized":
        return fail("Unauthorized callback", 401)
    if auth_error == "forbidden":
        return fail("Forbidden callback source", 403)
    if auth_error == "expired":
        return fail("Expired callback token", 401)

    payload = request.get_json() or {}
    callback_id = payload.get("callback_id")
    if not callback_id:
        return fail("Missing callback_id", 400)

    current_app.logger.info(
        "checker_callback_received callback_id=%s job_id=%s status=%s",
        callback_id,
        payload.get("job_id"),
        payload.get("status"),
    )

    if integrations_service.callback_is_duplicate(payload, callback_id):
        current_app.logger.info("checker_callback_duplicate callback_id=%s", callback_id)
        return ok({"status": "ok", "duplicate": True})

    submission = integrations_service.apply_checker_result(payload)
    if submission is None:
        current_app.logger.warning("checker_callback_submission_not_found callback_id=%s", callback_id)
        return fail("Submission not found", 404)

    integrations_service.mark_callback_processed(payload, callback_id)
    current_app.logger.info("checker_callback_processed callback_id=%s", callback_id)
    return ok()
