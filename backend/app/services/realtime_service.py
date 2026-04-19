from ..extensions import socketio


def emit_queue_updated(battle_id, payload=None):
    socketio.emit('queue_updated', payload or {}, room=f'battle:{battle_id}')


def emit_battle_status_changed(battle_id, status):
    socketio.emit('battle_status_changed', {'battle_id': str(battle_id), 'status': status}, room=f'battle:{battle_id}')


def emit_match_found(room_info):
    participant_ids = room_info.get('participant_ids', [])
    payload = {
        'room_id': room_info.get('room_id'),
        'match_id': room_info.get('match_id'),
        'task_id': room_info.get('task_id'),
        'participant_ids': participant_ids,
    }
    for uid in participant_ids:
        socketio.emit('match_found', payload, room=f'user:{uid}')
    if room_info.get('room_id'):
        socketio.emit('room_started', payload, room=f"room:{room_info['room_id']}")


def emit_submission_queued(match_id, student_id, battle_id=None):
    payload = {
        'match_id': str(match_id),
        'student_id': str(student_id),
    }
    socketio.emit('submission_queued', payload, room=f'match:{match_id}')
    if battle_id:
        socketio.emit('submission_queued', payload, room=f'battle:{battle_id}')


def emit_submission_verdict(match_id, student_id, verdict, progress, battle_id=None, visible_tests_passed=None, visible_tests_total=None):
    payload = {
        'match_id': str(match_id),
        'student_id': str(student_id),
        'verdict': verdict,
        'progress': progress,
        'visible_tests_passed': visible_tests_passed,
        'visible_tests_total': visible_tests_total,
    }
    socketio.emit('submission_verdict', payload, room=f'match:{match_id}')
    if battle_id:
        socketio.emit('submission_verdict', payload, room=f'battle:{battle_id}')


def emit_round_finished(match_id, finished_by):
    socketio.emit('round_finished', {'match_id': str(match_id), 'finished_by': finished_by}, room=f'match:{match_id}')


def emit_leaderboard_updated(battle_id):
    socketio.emit('leaderboard_updated', {'battle_id': str(battle_id)}, room=f'battle:{battle_id}')


def emit_presence_updated(*, battle_ids=None, room_ids=None, match_ids=None):
    payload = {
        "battle_ids": battle_ids or [],
        "room_ids": room_ids or [],
        "match_ids": match_ids or [],
    }
    for battle_id in payload["battle_ids"]:
        socketio.emit('presence_updated', payload, room=f'battle:{battle_id}')
    for room_id in payload["room_ids"]:
        socketio.emit('presence_updated', payload, room=f'room:{room_id}')
    for match_id in payload["match_ids"]:
        socketio.emit('presence_updated', payload, room=f'match:{match_id}')
