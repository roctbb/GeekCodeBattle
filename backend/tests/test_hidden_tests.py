import json
from copy import deepcopy
from uuid import UUID

import pytest

from test_reliability import setup_room


def configure_tests(app, room, tests, *, snapshot=False):
    from app.extensions import db
    from app.models import Match, Task
    from app.services.reports_service import public_task

    with app.app_context():
        match = db.session.get(Match, UUID(room['match_id']))
        task = db.session.get(Task, match.task_id)
        task.config_json = {'tests': tests, 'time_limit': 3}
        if snapshot:
            match.task_snapshot = public_task(task)
        db.session.commit()
        return str(task.id)


def test_hiding_tests_during_pending_submission_preserves_round_and_scoring(app, monkeypatch):
    from app.extensions import db
    from app.models import Battle, Match, Room, Submission
    from app.services import rooms_service

    teacher, battle, players, room = setup_room(app)
    student = players[0][0]
    tests = [
        {'input': 'secret-input-first', 'expected': 'secret-answer-first'},
        {'input': '1 2', 'expected': '3'},
        {'input': 'secret-input-last', 'expected': 'secret-answer-last'},
    ]
    task_id = configure_tests(app, room, tests, snapshot=True)
    captured = []

    def checker(**payload):
        captured.append(deepcopy(payload['check_config']))
        return {'job_id': payload['callback_id']}

    monkeypatch.setattr(rooms_service, 'submit_for_check', checker)
    url = f"/api/v1/rooms/{room['room_id']}"
    before = student.get(url).get_json()
    first = student.post(url + '/submit', json={'language': 'python', 'source_code': 'print(3)'})
    assert first.status_code == 202
    first_id = first.get_json()['submission_id']

    # Simulate the later DB change while a checker job is still in flight.
    marked = [{**test, 'hidden': index != 1} for index, test in enumerate(tests)]
    configure_tests(app, room, marked)
    after = student.get(url).get_json()
    assert after['match_id'] == before['match_id']
    assert after['status'] == 'active'
    assert after['round']['started_at'] == before['round']['started_at']
    assert after['round']['deadline_at'] == before['round']['deadline_at']
    assert after['my_submission']['verdict'] == 'queued'
    assert after['task']['public_tests'] == [{'input': '1 2', 'expected': '3', 'passed': None, 'actual': None}]
    assert teacher.get(f'/api/v1/tasks/{task_id}').get_json()['config']['tests'] == marked

    details = [
        {'input': test['input'], 'expected': test['expected'],
         'got': '3' if index == 1 else 'secret-output', 'ok': index == 1}
        for index, test in enumerate(tests)
    ]
    callback = teacher.post('/api/v1/integrations/geekpaste/callback', json={
        'callback_id': first_id, 'status': 'success', 'points': 1, 'max_points': 3,
        'comment': 'secret-input-first: secret-answer-first', 'details': details,
    })
    assert callback.status_code == 200
    current = student.get(url).get_json()
    assert current['task']['public_tests'] == [{'input': '1 2', 'expected': '3', 'passed': True, 'actual': '3'}]
    assert current['my_submission']['verdict'] == 'wrong_answer'
    assert 'secret-' not in json.dumps(current)
    report = student.get(f'/api/v1/me/results/{battle}').get_json()
    assert 'secret-' not in json.dumps(report)
    task_report = report['students'][0]['tasks'][0]
    assert task_report['public_tests'] == [{'input': '1 2', 'expected': '3'}]
    assert task_report['submissions'][0]['comment'] == 'Не все тесты пройдены.'

    # Submitting again includes every test in its original order and all options.
    second = student.post(url + '/submit', json={'language': 'python', 'source_code': 'print(4)'})
    assert second.status_code == 202
    assert captured[0] == {'tests': tests, 'time_limit': 3}
    assert captured[1] == {'tests': marked, 'time_limit': 3}
    with app.app_context():
        assert db.session.get(Battle, UUID(battle)).status == 'running'
        assert db.session.get(Room, UUID(room['room_id'])).status == 'active'
        match = db.session.get(Match, UUID(room['match_id']))
        assert match.finished_at is None
        # Filtering old snapshots is read-only; history is not rewritten.
        assert len(match.task_snapshot['public_tests']) == 3
        assert float(db.session.get(Submission, UUID(first_id)).progress_value) == pytest.approx(1 / 3, abs=0.0001)

    teacher.post('/api/v1/integrations/geekpaste/callback', json={
        'callback_id': second.get_json()['submission_id'], 'status': 'success',
        'points': 3, 'max_points': 3, 'details': [{**d, 'ok': True} for d in details],
    })
    assert student.get(url).get_json()['my_submission']['verdict'] == 'accepted'


@pytest.mark.parametrize('comment', [
    'secret-input', {'details': [{'input': 'secret-input', 'error': 'secret-output'}]},
    [{'stdout': 'secret-output'}], {'error': 'secret-answer'},
])
def test_single_hidden_test_and_checker_feedback_stay_private(app, comment):
    from app.extensions import db
    from app.models import Submission
    from app.services.reports_service import public_task
    from app.models import Task

    teacher, battle, players, room = setup_room(app)
    student = players[0][0]
    tests = [{'input': 'secret-input', 'expected': 'secret-answer', 'hidden': True}]
    task_id = configure_tests(app, room, tests, snapshot=True)
    url = f"/api/v1/rooms/{room['room_id']}"
    response = student.post(url + '/submit', json={'language': 'python', 'source_code': 'print(3)'})
    sub_id = response.get_json()['submission_id']
    teacher.post('/api/v1/integrations/geekpaste/callback', json={
        'callback_id': sub_id, 'status': 'error', 'comment': comment,
    })
    for path in [url, f'/api/v1/me/results/{battle}']:
        body = student.get(path).get_json()
        assert 'secret-' not in json.dumps(body)
    assert student.get(url).get_json()['task']['public_tests'] == []
    with app.app_context():
        assert public_task(db.session.get(Task, UUID(task_id)))['public_tests'] == []
        assert 'secret-' in db.session.get(Submission, UUID(sub_id)).checker_comment_raw


@pytest.mark.parametrize('payload, expected', [
    ({'details': [{'got': 'secret', 'ok': False}, {'got': 'public', 'ok': True}]}, 'public'),
    ({'visible_tests': [{'got': 'public', 'ok': True}]}, 'public'),
    ({'details': [{'got': 'secret', 'ok': False}]}, None),
    ({'visible_tests_passed': 1, 'visible_tests_total': 2}, None),
])
def test_hidden_result_alignment_fails_closed(app, payload, expected):
    from types import SimpleNamespace
    from app.routes.rooms import _extract_visible_test_results

    submission = SimpleNamespace(checker_comment_raw=json.dumps(payload), visible_tests_passed=1, visible_tests_total=2)
    tests = [{'hidden': True}, {'hidden': False}]
    results = _extract_visible_test_results(submission, tests)
    actual = results[1].get('actual') if len(results) > 1 else None
    assert actual == expected
