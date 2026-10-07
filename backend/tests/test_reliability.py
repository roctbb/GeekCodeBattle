from datetime import datetime, timezone
from uuid import UUID

from test_flow import login_dev, create_task_and_battle


def setup_room(app):
    app.config['MATCHMAKING_DELAY_SECONDS'] = 0
    teacher = app.test_client()
    login_dev(teacher, 'teacher-sec', 'Teacher', 'teacher')
    battle = create_task_and_battle(teacher)
    players = []
    for i in range(2):
        client = app.test_client()
        user = login_dev(client, f'player-{i}', f'Player {i}', 'student')
        client.post(f'/api/v1/battles/{battle}/queue/join', json={'code': 'B' + battle[:8]})
        client.post(f'/api/v1/battles/{battle}/queue/ready')
        players.append((client, user))
    room = players[0][0].get(f'/api/v1/battles/{battle}/my-room').get_json()
    return teacher, battle, players, room


def test_socket_and_http_object_access(app):
    from app.extensions import socketio
    from app.services.realtime_service import emit_submission_verdict
    teacher, battle, players, room = setup_room(app)
    anon = socketio.test_client(app)
    assert not anon.is_connected()
    outsider = app.test_client()
    login_dev(outsider, 'outsider', 'Other', 'student')
    sock = socketio.test_client(app, flask_test_client=outsider)
    assert sock.emit('subscribe', {'match_id': room['match_id']}, callback=True)['error'] == 'Forbidden'
    assert sock.emit('subscribe', {'room_id': room['room_id']}, callback=True)['error'] == 'Forbidden'
    assert outsider.get(f"/api/v1/rooms/{room['room_id']}").status_code == 403
    assert outsider.get(f"/api/v1/matches/{room['match_id']}").status_code == 403
    assert outsider.get(f"/api/v1/matches/{room['match_id']}/participants").status_code == 403
    for path in ['/tasks', '/task-packages', f'/battles/{battle}/tasks']:
        assert outsider.get('/api/v1' + path).status_code == 403
    with app.app_context():
        emit_submission_verdict(room['match_id'], players[0][1]['id'], 'accepted', 1, battle_id=battle)
    assert not [e for e in sock.get_received() if e['name'] == 'submission_verdict']
    sock.disconnect()


def test_authorized_subscription_receives_one_verdict(app):
    from app.extensions import socketio
    from app.services.realtime_service import emit_submission_verdict
    teacher, battle, players, room = setup_room(app)
    sock = socketio.test_client(app, flask_test_client=teacher)
    assert sock.emit('subscribe', {'battle_id': battle, **room}, callback=True)['status'] == 'subscribed'
    with app.app_context():
        emit_submission_verdict(room['match_id'], players[0][1]['id'], 'accepted', 1, battle_id=battle)
    assert len([e for e in sock.get_received() if e['name'] == 'submission_verdict']) == 1
    sock.disconnect()


def test_reconnect_snapshot_and_rejudge_replay(app):
    from app.extensions import db
    from app.models import Match, MatchParticipant, Room, User, ScoreEvent, RatingHistory, AuditLog
    from app.services.scoring_service import finalize_match, award_instant_winner_points
    teacher, battle, players, room = setup_room(app)
    a, b = [UUID(p[1]['id']) for p in players]
    state = players[0][0].get('/api/v1/me/state').get_json()
    assert state['room_id'] == room['room_id']
    with app.app_context():
        first = db.session.get(Match, UUID(room['match_id']))
        p = MatchParticipant.query.filter_by(match_id=first.id, student_id=a).one()
        p.accepted_at = datetime.now(timezone.utc)
        p.progress = 1
        db.session.commit()
        award_instant_winner_points(first, a)
        finalize_match(first)
        second_room = Room(battle_id=UUID(battle), status='active', started_at=datetime.now(timezone.utc))
        db.session.add(second_room)
        db.session.flush()
        second = Match(room_id=second_room.id, task_id=first.task_id)
        db.session.add(second)
        db.session.flush()
        db.session.add_all([
            MatchParticipant(match_id=second.id, student_id=a, progress=1, accepted_at=datetime.now(timezone.utc)),
            MatchParticipant(match_id=second.id, student_id=b, progress=0),
        ])
        db.session.commit()
        finalize_match(second)
        assert db.session.get(User, a).season_points == 290
        old_rating = db.session.get(User, a).rating
        second_id = second.id
    payload = {'reason': 'Correct the winner', 'new_results': [
        {'student_id': str(a), 'result_type': 'loss'}, {'student_id': str(b), 'result_type': 'win'},
    ]}
    assert teacher.post(f"/api/v1/matches/{room['match_id']}/rejudge", json=payload).status_code == 200
    with app.app_context():
        ua, ub = db.session.get(User, a), db.session.get(User, b)
        assert ua.season_points == 210  # first loss 30+40; second win 100+40, no streak bonus
        assert ub.season_points == 130
        assert ua.win_streak == 1 and ub.loss_streak == 1
        assert ua.rating < old_rating
        assert RatingHistory.query.filter_by(match_id=second_id, user_id=a).one().old_rating == 988
        count = ScoreEvent.query.count()
        points, rating = ua.season_points, ua.rating
        assert AuditLog.query.filter_by(action='rejudge').count() == 1
    assert teacher.post(f"/api/v1/matches/{room['match_id']}/rejudge", json=payload).status_code == 200
    with app.app_context():
        ua = db.session.get(User, a)
        assert (ua.season_points, ua.rating, ScoreEvent.query.count()) == (points, rating, count)
    last = players[0][0].get('/api/v1/me/state').get_json()
    assert last['room_id'] is None
    assert last['last_result']['result_type'] == 'win'
    assert last['me']['win_streak'] == 1


def test_pending_submission_and_duplicate_callback(app):
    from app.extensions import db
    from app.models import ScoreEvent
    teacher, battle, players, room = setup_room(app)
    player = players[0][0]
    url = f"/api/v1/rooms/{room['room_id']}/submit"
    assert player.post(url, json={'language': 'python', 'source_code': ''}).status_code == 400
    submitted = player.post(url, json={'language': 'python', 'source_code': 'print(3)'})
    assert submitted.status_code == 202
    assert player.post(url, json={'language': 'python', 'source_code': 'print(3)'}).status_code == 409
    payload = {'callback_id': submitted.get_json()['submission_id'], 'status': 'success', 'points': 1, 'max_points': 1}
    callback = '/api/v1/integrations/geekpaste/callback'
    assert teacher.post(callback, json=payload).status_code == 200
    assert teacher.post(callback, json=payload).status_code == 200
    with app.app_context():
        assert ScoreEvent.query.count() == 1
    assert player.get('/api/v1/me/state').get_json()['last_result']['result_type'] == 'win'


def test_proxy_protocol_and_stale_role(app):
    from werkzeug.middleware.proxy_fix import ProxyFix
    from app.extensions import db
    from app.models import User
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=2, x_proto=1)
    app.add_url_rule('/test-scheme', view_func=lambda: __import__('flask').request.scheme)
    teacher = app.test_client()
    user = login_dev(teacher, 'role-change', 'Teacher', 'teacher')
    assert teacher.get('/test-scheme', headers={'X-Forwarded-Proto': 'https'}).text == 'https'
    with app.app_context():
        db.session.get(User, UUID(user['id'])).role = 'student'
        db.session.commit()
    assert teacher.get('/api/v1/tasks').status_code == 403


def test_checker_transport_error_does_not_overwrite_received_verdict(app, monkeypatch):
    from app.services import rooms_service, integrations_service
    teacher, battle, players, room = setup_room(app)

    def accepted_then_timeout(**kwargs):
        integrations_service.apply_checker_result({
            'callback_id': kwargs['callback_id'], 'status': 'success', 'points': 1, 'max_points': 1,
        })
        raise TimeoutError('Checker response was lost after callback')

    monkeypatch.setattr(rooms_service, 'submit_for_check', accepted_then_timeout)
    player = players[0][0]
    response = player.post(f"/api/v1/rooms/{room['room_id']}/submit", json={
        'language': 'python', 'source_code': 'print(3)',
    })
    assert response.status_code == 202
    assert response.get_json()['status'] == 'accepted'
    assert player.get('/api/v1/me/state').get_json()['last_result']['points'] == 140
    assert player.get(f"/api/v1/rooms/{room['room_id']}").get_json()['my_submission']['verdict'] == 'accepted'


def test_invalid_auth_callback_returns_explicit_error(app):
    from urllib.parse import urlparse, parse_qs
    client = app.test_client()
    response = client.get('/api/v1/auth/callback?token=invalid&next=/packages?filter=mine')
    target = urlparse(response.headers['Location'])
    assert target.path == '/packages'
    assert parse_qs(target.query) == {'filter': ['mine'], 'auth_error': ['invalid_token']}
    assert client.get('/api/v1/me').status_code == 401
