import json
from types import SimpleNamespace

import pytest

from test_hidden_tests import configure_tests
from test_reliability import setup_room


@pytest.mark.parametrize('verdict, message', [
    ('compilation_error', 'Ошибка компиляции.'),
    ('runtime_error', 'Ошибка времени выполнения.'),
    ('time_limit_exceeded', 'Превышен лимит времени.'),
    ('output_limit_exceeded', 'Превышен лимит вывода.'),
    ('internal_error', 'Ошибка проверки решения.'),
    ('wrong_answer', 'Не все тесты пройдены.'),
    ('accepted', 'Все тесты пройдены.'),
])
def test_room_history_and_socket_show_safe_reason_and_all_test_counts(app, verdict, message):
    from app.extensions import socketio

    teacher, battle, players, room = setup_room(app)
    player = players[0][0]
    configure_tests(app, room, [
        {'input': '1 2', 'expected': '3'},
        {'input': 'SECRET_INPUT', 'expected': 'SECRET_EXPECTED', 'hidden': True},
        {'input': 'SECRET_INPUT_2', 'expected': 'SECRET_EXPECTED_2', 'hidden': True},
    ], snapshot=True)
    sock = socketio.test_client(app, flask_test_client=player)
    assert sock.emit('subscribe', {'match_id': room['match_id']}, callback=True)['status'] == 'subscribed'
    path = f"/api/v1/rooms/{room['room_id']}"
    response = player.post(path + '/submit', json={'language': 'python', 'source_code': 'print(3)'})
    assert response.status_code == 202
    pending = player.get(path).get_json()['my_submission']
    assert pending['tests_passed'] is None and pending['tests_total'] is None
    passed = 3 if verdict == 'accepted' else 0 if verdict == 'compilation_error' else 1
    payload = {
        'callback_id': response.get_json()['submission_id'],
        'status': 'error' if verdict == 'internal_error' else 'success',
        'verdict': verdict, 'error_type': None if verdict in {'accepted', 'wrong_answer'} else verdict,
        'points': passed, 'max_points': 3, 'tests_passed': passed, 'tests_total': 3,
        'comment': 'SECRET_COMMENT',
        'details': [{'input': '1 2', 'expected': '3', 'got': '3', 'ok': passed > 0},
                    {'input': 'SECRET_INPUT', 'expected': 'SECRET_EXPECTED', 'got': 'SECRET_OUTPUT',
                     'error': 'SECRET_STDERR', 'ok': verdict == 'accepted'},
                    {'input': 'SECRET_INPUT_2', 'got': 'SECRET_OUTPUT_2', 'ok': verdict == 'accepted'}],
    }
    assert teacher.post('/api/v1/integrations/geekpaste/callback', json=payload).status_code == 200
    current = player.get(path).get_json()
    submission = current['my_submission']
    assert submission['verdict'] == verdict
    assert submission['checker_message'] == message
    assert (submission['tests_passed'], submission['tests_total']) == (passed, 3)
    report = player.get(f'/api/v1/me/results/{battle}').get_json()
    history = report['students'][0]['tasks'][0]['submissions'][0]
    assert history['verdict'] == verdict
    assert history['comment'] == message
    assert (history['tests_passed'], history['tests_total']) == (passed, 3)
    events = [event for event in sock.get_received() if event['name'] == 'submission_verdict']
    assert len(events) == 1
    assert events[0]['args'][0]['verdict'] == verdict
    assert events[0]['args'][0]['tests_passed'] == passed
    assert events[0]['args'][0]['tests_total'] == 3
    for body in (current, report, events):
        assert 'SECRET' not in json.dumps(body)
    # Duplicate callbacks cannot erase the persisted count or safe reason.
    assert teacher.post('/api/v1/integrations/geekpaste/callback', json={
        'callback_id': payload['callback_id'], 'status': 'success', 'points': 0, 'max_points': 1,
    }).status_code == 200
    assert player.get(path).get_json()['my_submission'] == submission
    sock.disconnect()


@pytest.mark.parametrize('diagnostic, verdict', [
    ('Runtime error: SECRET_INPUT', 'runtime_error'),
    ('Test failed: Execution timed out after 5 seconds.', 'time_limit_exceeded'),
])
def test_legacy_geekpaste_per_test_error_and_score_counts(app, diagnostic, verdict):
    teacher, battle, players, room = setup_room(app)
    player = players[0][0]
    configure_tests(app, room, [{'input': 'SECRET_INPUT', 'expected': 'SECRET_EXPECTED', 'hidden': True}])
    path = f"/api/v1/rooms/{room['room_id']}"
    submission_id = player.post(path + '/submit', json={'language': 'python', 'source_code': 'print(3)'}).get_json()['submission_id']
    teacher.post('/api/v1/integrations/geekpaste/callback', json={
        'callback_id': submission_id, 'status': 'success', 'points': 0, 'max_points': 1,
        'comment': '0 из 1 тестов пройдено', 'details': [{'ok': False, 'error': diagnostic}],
    })
    body = player.get(path).get_json()
    assert body['my_submission']['verdict'] == verdict
    assert body['my_submission']['tests_passed'] == 0
    assert body['my_submission']['tests_total'] == 1
    assert 'SECRET' not in json.dumps(body)


def test_legacy_compile_failure_uses_config_total_instead_of_default_one(app):
    teacher, _, players, room = setup_room(app)
    player = players[0][0]
    configure_tests(app, room, [{'input': str(i), 'expected': str(i), 'hidden': True} for i in range(4)])
    path = f"/api/v1/rooms/{room['room_id']}"
    submission_id = player.post(path + '/submit', json={'language': 'cpp', 'source_code': 'broken'}).get_json()['submission_id']
    teacher.post('/api/v1/integrations/geekpaste/callback', json={
        'callback_id': submission_id, 'status': 'error', 'points': 0, 'max_points': 1,
        'comment': 'Compilation failed: SECRET_COMPILER_OUTPUT',
    })
    submission = player.get(path).get_json()['my_submission']
    assert submission['verdict'] == 'compilation_error'
    assert (submission['tests_passed'], submission['tests_total']) == (0, 4)
    assert submission['checker_message'] == 'Ошибка компиляции.'


def test_public_runtime_diagnostics_are_not_hidden_by_summary_comment(app):
    teacher, battle, players, room = setup_room(app)
    player = players[0][0]
    path = f"/api/v1/rooms/{room['room_id']}"
    submission_id = player.post(path + '/submit', json={'language': 'python', 'source_code': 'print(1/0)'}).get_json()['submission_id']
    diagnostic = 'Runtime error: ZeroDivisionError: division by zero'
    teacher.post('/api/v1/integrations/geekpaste/callback', json={
        'callback_id': submission_id, 'status': 'success', 'points': 0, 'max_points': 1,
        'comment': '0 из 1 тестов пройдено', 'details': [{'ok': False, 'error': diagnostic}],
    })
    assert player.get(path).get_json()['my_submission']['checker_message'] == diagnostic
    report = player.get(f'/api/v1/me/results/{battle}').get_json()
    assert report['students'][0]['tasks'][0]['submissions'][0]['comment'] == diagnostic


def test_practice_shows_error_and_example_counts_without_including_hidden_tests(app):
    teacher, _, players, room = setup_room(app)
    player = players[0][0]
    configure_tests(app, room, [{'input': '1', 'expected': '2'},
                                {'input': 'SECRET', 'expected': 'SECRET', 'hidden': True}])
    path = f"/api/v1/rooms/{room['room_id']}/runs"
    run_id = player.post(path, json={'language': 'python', 'source_code': 'print(1/0)'}).get_json()['id']
    teacher.post('/api/v1/integrations/geekpaste/run-callback', json={
        'callback_id': run_id, 'status': 'success', 'points': 0, 'max_points': 1,
        'tests_passed': 0, 'tests_total': 1, 'error_type': 'runtime_error',
        'comment': '0 из 1 тестов пройдено', 'details': [{'ok': False, 'error': 'Runtime error: division by zero'}],
    })
    result = player.get(f'{path}/{run_id}').get_json()
    assert result['verdict'] == 'runtime_error'
    assert result['message'] == 'Runtime error: division by zero'
    assert (result['tests_passed'], result['tests_total']) == (0, 1)
    assert 'SECRET' not in json.dumps(result)


def test_saved_legacy_results_keep_original_count_and_safe_error_without_rechecking():
    from app.services.checker_feedback import submission_test_counts, submission_verdict
    sub = SimpleNamespace(verdict='wrong_answer', checker_status_raw='success', checker_comment_raw=json.dumps({
        'comment': '4 из 7 тестов пройдено', 'details': [{'error': 'Runtime error: SECRET'}],
    }))
    assert submission_test_counts(sub) == {'tests_passed': 4, 'tests_total': 7}
    assert submission_verdict(sub) == 'runtime_error'


@pytest.mark.parametrize('invalid', [True, -1, 1.5, '2', [], {}])
def test_untrusted_metadata_cannot_become_counts_or_error_labels(invalid):
    from app.services.checker_feedback import checker_test_counts, checker_error_type
    assert checker_test_counts({'tests_passed': invalid, 'tests_total': 3}) == (None, None)
    assert checker_error_type({'error_type': invalid, 'details': [{'error_type': invalid}]}) is None


def test_gpt_scores_are_never_interpreted_as_test_counts():
    from app.services.checker_feedback import checker_test_counts
    assert checker_test_counts({'status': 'success', 'points': 3, 'max_points': 5}, check_type='gpt') == (None, None)
