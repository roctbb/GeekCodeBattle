from flask import Blueprint
from ..auth import login_required, role_required, current_user
from ..access import is_battle_member
from ..api.responses import ok, fail
from ..extensions import db
from ..models import BattleMember
from ..utils import as_uuid
from ..services.battles_service import get_battle_or_none
from ..services.reports_service import battle_report, my_results

results_bp = Blueprint('results', __name__, url_prefix='/api/v1')


@results_bp.get('/me/results')
@login_required
def results():
    return ok(my_results(current_user()))


@results_bp.get('/me/results/<battle_id>')
@login_required
def my_result(battle_id):
    battle = get_battle_or_none(battle_id)
    user = current_user()
    if not is_battle_member(user, battle):
        return fail('Результат недоступен.', 403)
    report = battle_report(battle, user_id=user.id, detail=True)
    report['students'][0].pop('place', None)
    return ok(report)


@results_bp.get('/battles/<battle_id>/statistics')
@role_required('teacher', 'admin')
def statistics(battle_id):
    battle = get_battle_or_none(battle_id)
    if not battle:
        return fail('Not found', 404)
    return ok(battle_report(battle))


@results_bp.get('/battles/<battle_id>/students/<student_id>/results')
@role_required('teacher', 'admin')
def student_result(battle_id, student_id):
    battle = get_battle_or_none(battle_id)
    try:
        uid = as_uuid(student_id)
    except (ValueError, TypeError):
        return fail('Участник не найден.', 404)
    if not battle or not db.session.get(BattleMember, (battle.id, uid)):
        return fail('Участник не найден.', 404)
    report = battle_report(battle, user_id=uid, detail=True)
    report['students'][0].pop('place', None)
    return ok(report)
