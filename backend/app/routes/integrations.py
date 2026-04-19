from flask import Blueprint, request, current_app

from ..api.responses import ok, fail
from ..services import integrations_service


integrations_bp = Blueprint("integrations", __name__, url_prefix="/api/v1/integrations")


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
