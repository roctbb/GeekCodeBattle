from flask import Blueprint, request, session

from ..api.responses import ok, fail
from ..api.serializers import participant_out
from ..api.validators import VALID_PARTICIPANT_RESULTS
from ..auth import login_required, role_required
from ..services import matches_service


matches_bp = Blueprint("matches", __name__, url_prefix="/api/v1")


@matches_bp.get("/matches/<match_id>")
@login_required
def get_match(match_id):
    match = matches_service.get_match_or_none(match_id)
    if not match:
        return fail("Not found", 404)
    return ok(
        {
            "id": str(match.id),
            "room_id": str(match.room_id),
            "task_id": str(match.task_id),
            "finished_by": match.finished_by,
            "finished_at": match.finished_at.isoformat() if match.finished_at else None,
        }
    )


@matches_bp.get("/matches/<match_id>/participants")
@login_required
def match_participants(match_id):
    match = matches_service.get_match_or_none(match_id)
    if not match:
        return fail("Not found", 404)
    return ok([participant_out(i) for i in matches_service.get_match_participants(match_id)])


@matches_bp.post("/matches/<match_id>/rejudge")
@role_required("teacher", "admin")
def rejudge(match_id):
    data = request.get_json() or {}
    reason = (data.get("reason") or "").strip()
    new_results = data.get("new_results")

    if not reason:
        return fail("reason is required", 400)
    if not isinstance(new_results, list) or not new_results:
        return fail("new_results is required", 400)
    for item in new_results:
        if item.get("result_type") not in VALID_PARTICIPANT_RESULTS:
            return fail("Invalid result_type", 400)

    _, error = matches_service.rejudge_match(
        match_id=match_id,
        actor_id=session["user_id"],
        reason=reason,
        new_results=new_results,
    )
    if error == "match_not_found":
        return fail("Not found", 404)
    if error == "missing_participants":
        return fail("new_results must include every room participant", 400)
    return ok()
