from uuid import UUID
from test_flow import login_dev, create_task_and_battle
from test_reliability import setup_room


def test_invite_required_to_open_start_and_join(app):
    teacher, student = app.test_client(), app.test_client()
    login_dev(teacher, 'invite-teacher', 'Teacher', 'teacher')
    login_dev(student, 'invite-student', 'Student', 'student')
    battle = teacher.post('/api/v1/battles', json={'title': 'Private'}).get_json()['id']
    for action in ['open-lobby', 'start']:
        assert teacher.post(f'/api/v1/battles/{battle}/{action}').status_code == 422
    assert student.get('/api/v1/battles').get_json() == []
    for path in ['', '/queue', '/leaderboard', '/my-room']:
        assert student.get(f'/api/v1/battles/{battle}{path}').status_code == 403
    assert student.post(f'/api/v1/battles/{battle}/queue/join').status_code == 403
    assert student.post(f'/api/v1/battles/{battle}/queue/ready').status_code == 403
    assert student.post('/api/v1/battles/join', json={'code': 'unknown'}).status_code == 404
    assert teacher.put(f'/api/v1/battles/{battle}/invite', json={'code': ' abcd-7a '}).get_json()['invite_code'] == 'ABCD-7A'
    assert student.post('/api/v1/battles/join', json={'code': 'abcd-7a'}).status_code == 409
    teacher.post(f'/api/v1/battles/{battle}/open-lobby')
    assert student.post(f'/api/v1/battles/{battle}/queue/join', json={'code': 'wrong'}).status_code == 403
    joined = student.post('/api/v1/battles/join', json={'code': ' abcd-7a '})
    assert joined.status_code == 200
    assert 'invite_code' not in joined.get_json()
    assert 'invite_code' not in student.get(f'/api/v1/battles/{battle}').get_json()
    assert 'invite_code' not in student.get('/api/v1/battles').get_json()[0]
    other = teacher.post('/api/v1/battles', json={'title': 'Other'}).get_json()['id']
    assert teacher.put(f'/api/v1/battles/{other}/invite', json={'code': 'ABCD-7A'}).status_code == 409
    assert teacher.put(f'/api/v1/battles/{other}/invite', json={'code': 'AB'}).status_code == 422
    # Rotating a code does not destroy admission or history.
    teacher.put(f'/api/v1/battles/{battle}/invite', json={'code': 'NEWCODE'})
    student.post(f'/api/v1/battles/{battle}/queue/leave')
    assert student.post(f'/api/v1/battles/{battle}/queue/join').status_code == 200
    assert student.get('/api/v1/me/results').get_json()[0]['attempts'] == 0


def test_uninvited_socket_gets_no_battle_events(app):
    from app.extensions import socketio
    from app.services.realtime_service import emit_battle_status_changed
    teacher, battle, players, room = setup_room(app)
    outsider = app.test_client()
    login_dev(outsider, 'uninvited', 'Other', 'student')
    sock = socketio.test_client(app, flask_test_client=outsider)
    assert sock.emit('subscribe', {'battle_id': battle}, callback=True)['error'] == 'Forbidden'
    with app.app_context():
        emit_battle_status_changed(battle, 'stopped')
    assert not [e for e in sock.get_received() if e['name'] == 'battle_status_changed']
    sock.disconnect()


def test_stop_results_statistics_and_own_solutions(app):
    from app.extensions import db
    from app.models import Task, Match
    teacher, battle, players, room = setup_room(app)
    student, user = players[0]
    other, other_user = players[1]
    nobody = app.test_client()
    login_dev(nobody, 'joined-no-round', 'No attempts', 'student')
    assert nobody.post('/api/v1/battles/join', json={'code': 'B'+battle[:8]}).status_code == 200
    # A task in the pool which has not been issued must not count as failed.
    extra = teacher.post('/api/v1/tasks', json={'title':'Unissued', 'statement_md':'Future task', 'difficulty':'easy', 'check_type':'tests', 'config':{}}).get_json()['id']
    teacher.post(f'/api/v1/battles/{battle}/tasks/{extra}')
    url = f"/api/v1/rooms/{room['room_id']}/submit"
    first = student.post(url, json={'language':'python','source_code':'print("wrong")'}).get_json()['submission_id']
    teacher.post('/api/v1/integrations/geekpaste/callback', json={'callback_id':first,'status':'success','points':0,'max_points':1})
    second = student.post(url, json={'language':'python','source_code':'print(3)'}).get_json()['submission_id']
    teacher.post('/api/v1/integrations/geekpaste/callback', json={'callback_id':second,'status':'success','points':1,'max_points':1})
    third = other.post(url, json={'language':'cpp','source_code':'other student private code'}).get_json()['submission_id']
    teacher.post('/api/v1/integrations/geekpaste/callback', json={'callback_id':third,'status':'success','points':0,'max_points':1})
    assert teacher.post(f'/api/v1/battles/{battle}/stop').status_code == 200
    state = student.get('/api/v1/me/state').get_json()
    assert state['room_id'] is None and state['battle_id'] is None and state['result_battle_id'] == battle
    assert student.post(f'/api/v1/battles/{battle}/queue/ready').status_code == 409
    assert student.post(url, json={'language':'python','source_code':'late'}).status_code == 400
    # Task descriptions in reports survive subsequent task edits.
    with app.app_context():
        match = db.session.get(Match, UUID(room['match_id']))
        task = db.session.get(Task, match.task_id)
        task.statement_md = 'Edited after the round'
        db.session.commit()
    report = student.get(f'/api/v1/me/results/{battle}').get_json()
    row = report['students'][0]
    assert (row['solved'], row['assigned'], row['unsolved'], row['not_assigned'], row['attempts']) == (1,1,0,1,2)
    task = next(t for t in row['tasks'] if t['assigned'])
    assert task['statement_md'] == 'sum two numbers'
    assert {s['verdict'] for s in task['submissions']} == {'accepted','wrong_answer'}
    assert {s['source_code'] for s in task['submissions']} == {'print(3)','print("wrong")'}
    assert 'other student private code' not in str(report)
    assert student.get(f'/api/v1/battles/{battle}/statistics').status_code == 403
    assert student.get(f"/api/v1/battles/{battle}/students/{other_user['id']}/results").status_code == 403
    outsider = app.test_client()
    login_dev(outsider, 'result-outsider', 'Outsider', 'student')
    assert outsider.get(f'/api/v1/me/results/{battle}').status_code == 403
    stats = teacher.get(f'/api/v1/battles/{battle}/statistics').get_json()
    assert stats['summary']['participants'] == 3
    assert stats['summary']['attempts'] == 3
    other_row = next(r for r in stats['students'] if r['user_id'] == other_user['id'])
    assert (other_row['solved'], other_row['unsolved'], other_row['not_assigned']) == (0,1,1)
    assert all('submissions' not in t for r in stats['students'] for t in r['tasks'])
    personal = teacher.get(f"/api/v1/battles/{battle}/students/{other_user['id']}/results").get_json()
    assert 'other student private code' in str(personal)
    # Resuming keeps admission and history but never silently marks pupils ready.
    assert teacher.post(f'/api/v1/battles/{battle}/start').status_code == 200
    assert student.post(f'/api/v1/battles/{battle}/queue/join').status_code == 200
    resumed = student.get('/api/v1/me/state').get_json()
    assert resumed['battle_id'] == battle and resumed['room_id'] is None
    queue = teacher.get(f'/api/v1/battles/{battle}/queue').get_json()
    assert not any(e['is_ready'] for e in queue['entries'])
    assert student.get(f'/api/v1/me/results/{battle}').get_json()['students'][0]['attempts'] == 2
    # Finalization is idempotent and final battles cannot be reopened or joined.
    before = row['points']
    assert teacher.post(f'/api/v1/battles/{battle}/finish').status_code == 200
    assert teacher.post(f'/api/v1/battles/{battle}/finish').status_code == 200
    for action in ['open-lobby','start']:
        assert teacher.post(f'/api/v1/battles/{battle}/{action}').status_code >= 400
    assert student.post('/api/v1/battles/join', json={'code':'B'+battle[:8]}).status_code == 409
    assert student.get(f'/api/v1/me/results/{battle}').get_json()['students'][0]['points'] == before


def test_stop_rolls_back_all_rooms_on_failure(app, monkeypatch):
    import pytest
    from app.extensions import db
    from app.models import Battle, Match, Room, ScoreEvent
    from app.services import battles_service
    teacher, battle_id, players, room = setup_room(app)
    for i in range(2):
        client = app.test_client()
        login_dev(client, f'extra-{i}', f'Extra {i}', 'student')
        client.post('/api/v1/battles/join', json={'code': 'B' + battle_id[:8]})
        client.post(f'/api/v1/battles/{battle_id}/queue/ready')
    real_finalize = battles_service.finalize_match
    calls = []

    def failing_finalize(*args, **kwargs):
        calls.append(args[0].id)
        if len(calls) == 2:
            raise RuntimeError('Temporary scoring failure')
        return real_finalize(*args, **kwargs)

    monkeypatch.setattr(battles_service, 'finalize_match', failing_finalize)
    with app.app_context():
        battle = db.session.get(Battle, UUID(battle_id))
        with pytest.raises(RuntimeError):
            battles_service.stop_battle(battle)
        db.session.rollback()
        assert len(calls) == 2
        assert db.session.get(Battle, UUID(battle_id)).status == 'running'
        assert Match.query.filter(Match.finished_at.is_not(None)).count() == 0
        assert Room.query.filter_by(status='active').count() == 2
        assert ScoreEvent.query.count() == 0
