from datetime import datetime, timedelta, timezone
from uuid import UUID
import json
import pytest

from test_reliability import setup_room


def test_practice_callback_never_awards_points_or_exposes_hidden_tests(app, monkeypatch):
    from app.extensions import db
    from app.models import Match, Task, Submission, MatchParticipant, User, ScoreEvent, RatingHistory
    from app.services import rooms_service
    teacher, battle, players, room = setup_room(app)
    player, user = players[0]
    captured = []
    monkeypatch.setattr(rooms_service, 'submit_for_check', lambda **kw: captured.append(kw) or {'job_id': 'practice'})
    with app.app_context():
        task = db.session.get(Task, db.session.get(Match, UUID(room['match_id'])).task_id)
        task.config_json = {'tests': [{'input': '1 2', 'expected': '3'}, {'input': 'SECRET', 'expected': 'SECRET RESULT', 'hidden': True}]}
        db.session.commit()
    response = player.post(f"/api/v1/rooms/{room['room_id']}/runs", json={'language': 'python', 'source_code': 'print(3)', 'kind': 'examples'})
    assert response.status_code == 202
    run_id = response.get_json()['id']
    assert response.get_json()['created_at'].endswith('+00:00')
    assert captured[0]['check_config'] == {'tests': [{'input': '1 2', 'expected': '3'}]}
    assert captured[0]['task_text'] == ''
    assert captured[0]['callback_url'].endswith('/run-callback')
    pending = player.post(f"/api/v1/rooms/{room['room_id']}/runs", json={'language': 'python', 'source_code': 'print(4)'})
    assert pending.status_code == 409
    assert pending.get_json()['error']['details']['run_id'] == run_id
    callback = {'callback_id': run_id, 'status': 'success', 'points': 1, 'max_points': 1, 'details': [{'passed': True, 'actual': '3'}]}
    assert teacher.post('/api/v1/integrations/geekpaste/run-callback', json=callback).status_code == 200
    assert teacher.post('/api/v1/integrations/geekpaste/run-callback', json=callback).get_json()['duplicate'] is True
    output = player.get(f"/api/v1/rooms/{room['room_id']}/runs/{run_id}").get_json()
    assert output['verdict'] == 'completed'
    assert output['tests'] == [{'input': '1 2', 'expected': '3', 'actual': '3', 'passed': True}]
    assert 'SECRET' not in str(output)
    assert players[1][0].get(f"/api/v1/rooms/{room['room_id']}/runs/{run_id}").status_code == 404
    # The other callback endpoint cannot mistake a practice job for a scored attempt.
    assert teacher.post('/api/v1/integrations/geekpaste/callback', json=callback).status_code == 404
    with app.app_context():
        assert Submission.query.count() == ScoreEvent.query.count() == RatingHistory.query.count() == 0
        assert db.session.get(User, UUID(user['id'])).season_points == 0
        assert MatchParticipant.query.filter_by(student_id=UUID(user['id'])).one().accepted_at is None


def test_custom_input_has_no_expected_answer_and_callback_requires_auth(app):
    teacher, _, players, room = setup_room(app)
    player = players[0][0]
    path = f"/api/v1/rooms/{room['room_id']}/runs"
    response = player.post(path, json={'language': 'cpp', 'source_code': 'int main(){}', 'kind': 'custom', 'input': 'my stdin'})
    run_id = response.get_json()['id']
    app.config['GEEKPASTE_CALLBACK_REQUIRE_AUTH'] = True
    payload = {'callback_id': run_id, 'status': 'success', 'details': [{'passed': False, 'output': '42\n'}]}
    assert teacher.post('/api/v1/integrations/geekpaste/run-callback', json=payload).status_code == 401
    assert player.get(f'{path}/{run_id}').get_json()['verdict'] == 'queued'
    app.config['GEEKPASTE_CALLBACK_REQUIRE_AUTH'] = False
    assert teacher.post('/api/v1/integrations/geekpaste/run-callback', json=payload).status_code == 200
    result = player.get(f'{path}/{run_id}').get_json()
    assert result['verdict'] == 'completed'
    assert result['tests'][0] == {'input': 'my stdin', 'expected': None, 'actual': '42\n', 'passed': None}


def test_countdown_hides_task_and_blocks_both_execution_paths(app):
    from app.extensions import db
    from app.models import Room
    app.config['ROUND_INTRO_SECONDS'] = 3
    _, battle, players, room = setup_room(app)
    player = players[0][0]
    path = f"/api/v1/rooms/{room['room_id']}"
    state = player.get(path).get_json()
    assert state['task'] is None
    assert state['round']['is_preparing'] is True
    assert state['round']['is_active'] is False
    report = player.get(f'/api/v1/me/results/{battle}').get_json()
    assert report['students'][0]['tasks'] == []
    code = {'language': 'python', 'source_code': 'print(3)'}
    assert player.post(path + '/submit', json=code).status_code == 409
    assert player.post(path + '/runs', json=code).status_code == 409
    with app.app_context():
        r = db.session.get(Room, UUID(room['room_id']))
        r.started_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.session.commit()
    state = player.get(path).get_json()
    assert state['task']['title'] == 'A+B'
    assert state['round']['is_preparing'] is False
    assert player.post(path + '/runs', json=code).status_code == 202


def test_run_limits_timeout_ownership_and_transport_error(app, monkeypatch):
    from app.extensions import db
    from app.models import CodeRun
    from app.services import rooms_service
    teacher, _, players, room = setup_room(app)
    player = players[0][0]
    path = f"/api/v1/rooms/{room['room_id']}/runs"
    outsider = app.test_client()
    from test_flow import login_dev
    login_dev(outsider, 'run-outsider', 'Other', 'student')
    code = {'language': 'python', 'source_code': 'print(3)'}
    assert outsider.post(path, json=code).status_code == 403
    assert player.post(path, json={**code, 'kind': 'invalid'}).status_code == 400
    assert player.post(path, json={**code, 'kind': 'custom', 'input': 'x' * 65537}).status_code == 400
    assert player.post(path, json={**code, 'source_code': 'x' * 262145}).status_code == 413
    run = player.post(path, json=code).get_json()
    with app.app_context():
        db.session.get(CodeRun, UUID(run['id'])).created_at = datetime.now(timezone.utc) - timedelta(
            seconds=app.config['SUBMISSION_CHECK_TIMEOUT_SECONDS'] + 1)
        db.session.commit()
    result = player.get(f"{path}/{run['id']}").get_json()
    assert result['verdict'] == 'internal_error'
    def fail(**kwargs): raise RuntimeError('unavailable')
    monkeypatch.setattr(rooms_service, 'submit_for_check', fail)
    assert player.post(path, json=code).get_json()['verdict'] == 'internal_error'


def test_reports_explain_actual_score_ledger(app):
    from app.extensions import db
    from app.models import Match, MatchParticipant
    from app.services.scoring_service import finalize_match
    _, battle, players, room = setup_room(app)
    with app.app_context():
        match = db.session.get(Match, UUID(room['match_id']))
        part = MatchParticipant.query.filter_by(match_id=match.id, student_id=UUID(players[0][1]['id'])).one()
        part.accepted_at = datetime.now(timezone.utc)
        part.progress = 1
        db.session.commit()
        finalize_match(match)
    report = players[0][0].get(f'/api/v1/me/results/{battle}').get_json()
    student = report['students'][0]
    rounds = student['tasks'][0]['score_rounds']
    assert sum(e['points'] for r in rounds for e in r['entries']) == student['points']
    assert rounds[0]['rating']['after'] - rounds[0]['rating']['before'] == student['rating_delta']


def test_code_run_migration_matches_model_and_is_reversible(app):
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect
    from app.extensions import db
    from app.models import CodeRun
    path = Path(__file__).parents[1] / 'migrations/versions/0006_code_runs.py'
    spec = importlib.util.spec_from_file_location('practice_migration', path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with app.app_context():
        CodeRun.__table__.drop(db.engine)
        with db.engine.begin() as connection:
            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
                assert {c['name'] for c in inspect(connection).get_columns('code_runs')} == set(CodeRun.__table__.columns.keys())
                migration.downgrade()
                assert 'code_runs' not in inspect(connection).get_table_names()
                migration.upgrade()


@pytest.mark.parametrize('comment', [
    {'tests': [{'passed': True, 'stdout': '3\n'}]},
    [{'passed': True, 'stdout': '3\n'}],
    json.dumps({'visible_tests': [{'passed': True, 'actual_output': '3\n'}]}),
])
def test_run_preserves_feedback_returned_inside_comment(app, comment):
    teacher, _, players, room = setup_room(app)
    player = players[0][0]
    path = f"/api/v1/rooms/{room['room_id']}/runs"
    run = player.post(path, json={'language': 'python', 'source_code': 'print(3)'}).get_json()
    assert teacher.post('/api/v1/integrations/geekpaste/run-callback', json={
        'callback_id': run['id'], 'status': 'success', 'comment': comment, 'details': [],
    }).status_code == 200
    output = player.get(f"{path}/{run['id']}").get_json()
    assert output['tests'][0]['actual'] == '3\n'
    assert output['tests'][0]['passed'] is True
    assert output['message'] is None


def test_run_keeps_compile_error_and_early_callback_on_transport_failure(app, monkeypatch):
    from app.services import rooms_service
    teacher, _, players, room = setup_room(app)
    def early_result(**kwargs):
        teacher.post('/api/v1/integrations/geekpaste/run-callback', json={
            'callback_id': kwargs['callback_id'], 'status': 'error',
            'comment': {'compile_error': 'main.cpp:4: missing semicolon'},
        })
        raise TimeoutError('Response lost after callback')
    monkeypatch.setattr(rooms_service, 'submit_for_check', early_result)
    response = players[0][0].post(f"/api/v1/rooms/{room['room_id']}/runs", json={
        'language': 'cpp', 'source_code': 'int main() { error }',
    })
    assert response.status_code == 202
    assert response.get_json()['message'] == 'main.cpp:4: missing semicolon'


def test_run_exposes_per_test_runtime_diagnostics_as_text(app):
    teacher, _, players, room = setup_room(app)
    player = players[0][0]
    path = f"/api/v1/rooms/{room['room_id']}/runs"
    run = player.post(path, json={'language': 'python', 'source_code': 'print(1/0)'}).get_json()
    teacher.post('/api/v1/integrations/geekpaste/run-callback', json={
        'callback_id': run['id'], 'status': 'success',
        'details': [{'passed': False, 'stderr': 'File "main.py", line 1\nZeroDivisionError'}],
    })
    output = player.get(f"{path}/{run['id']}").get_json()
    assert output['message'] == 'File "main.py", line 1\nZeroDivisionError'
    assert output['tests'][0]['passed'] is False


@pytest.mark.parametrize('finished', ['accepted', 'surrendered'])
def test_cannot_run_after_finishing_own_round(app, monkeypatch, finished):
    from app.extensions import db
    from app.models import MatchParticipant, CodeRun
    from app.services import rooms_service
    _, _, players, room = setup_room(app)
    with app.app_context():
        participant = MatchParticipant.query.filter_by(
            match_id=UUID(room['match_id']), student_id=UUID(players[0][1]['id'])).one()
        if finished == 'accepted':
            participant.accepted_at = datetime.now(timezone.utc)
        else:
            participant.result_type = 'loss'
        db.session.commit()
    calls = []
    monkeypatch.setattr(rooms_service, 'submit_for_check', lambda **kw: calls.append(kw))
    response = players[0][0].post(f"/api/v1/rooms/{room['room_id']}/runs", json={
        'language': 'python', 'source_code': 'print(3)',
    })
    assert response.status_code == 409
    assert calls == []
    with app.app_context():
        assert CodeRun.query.count() == 0
