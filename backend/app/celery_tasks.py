from .celery_app import celery
from .services import battles_service


@celery.task(name="app.celery_tasks.tick_all_battles_timeouts_task")
def tick_all_battles_timeouts_task():
    finalized_total = 0
    for battle in battles_service.list_running_battles():
        finalized_total += int(battles_service.tick_timeouts(battle) or 0)
    return finalized_total


@celery.task(name="app.celery_tasks.delayed_tick_battles_task")
def delayed_tick_battles_task(battle_ids):
    finalized_total = 0
    for battle_id in battle_ids or []:
        battle = battles_service.get_battle_or_none(battle_id)
        if not battle:
            continue
        finalized_total += int(battles_service.tick_timeouts(battle) or 0)
    return finalized_total
