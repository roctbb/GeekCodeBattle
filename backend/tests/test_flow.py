import time
from datetime import datetime, timezone, timedelta


def login_dev(client, external_id, name, role):
    r = client.post('/api/v1/auth/dev-login', json={
        'external_id': external_id,
        'name': name,
        'role': role,
    })
    assert r.status_code == 200
    return r.get_json()


def create_task_and_battle(teacher_client):
    rt = teacher_client.post('/api/v1/tasks', json={
        'title': 'A+B',
        'statement_md': 'sum two numbers',
        'difficulty': 'easy',
        'check_type': 'tests',
        'config': {'tests': [{'input': '1 2', 'expected': '3'}]},
    })
    assert rt.status_code == 201
    task_id = rt.get_json()['id']

    rb = teacher_client.post('/api/v1/battles', json={'title': 'B1', 'room_size': 2})
    assert rb.status_code == 201
    battle_id = rb.get_json()['id']

    assert teacher_client.post(f'/api/v1/battles/{battle_id}/tasks/{task_id}').status_code == 200
    assert teacher_client.post(f'/api/v1/battles/{battle_id}/open-lobby').status_code == 200
    assert teacher_client.post(f'/api/v1/battles/{battle_id}/start').status_code == 200

    return battle_id


def test_odd_players_form_room_of_three(app):
    teacher = app.test_client()
    login_dev(teacher, 'teacher-1', 'Teacher', 'teacher')
    battle_id = create_task_and_battle(teacher)

    students = []
    for i in range(1, 4):
        c = app.test_client()
        login_dev(c, f'student-{i}', f'S{i}', 'student')
        assert c.post(f'/api/v1/battles/{battle_id}/queue/join').status_code == 200
        assert c.post(f'/api/v1/battles/{battle_id}/queue/ready').status_code == 200
        students.append(c)

    room_ids = []
    for c in students:
        r = c.get(f'/api/v1/battles/{battle_id}/my-room')
        assert r.status_code == 200
        room_ids.append(r.get_json()['room_id'])

    assert len(set(room_ids)) == 1


def test_queue_state_endpoint(app):
    teacher = app.test_client()
    login_dev(teacher, 'teacher-q', 'Teacher', 'teacher')
    battle_id = create_task_and_battle(teacher)

    s1 = app.test_client()
    login_dev(s1, 's1', 'S1', 'student')
    s1.post(f'/api/v1/battles/{battle_id}/queue/join')

    r = teacher.get(f'/api/v1/battles/{battle_id}/queue')
    assert r.status_code == 200
    data = r.get_json()
    assert data['battle_id'] == battle_id
    assert len(data['entries']) == 1


def test_rejudge_requires_all_participants(app):
    teacher = app.test_client()
    login_dev(teacher, 'teacher-r', 'Teacher', 'teacher')
    battle_id = create_task_and_battle(teacher)

    s1 = app.test_client()
    login_dev(s1, 'rs1', 'RS1', 'student')
    s2 = app.test_client()
    login_dev(s2, 'rs2', 'RS2', 'student')

    s1.post(f'/api/v1/battles/{battle_id}/queue/join')
    s1.post(f'/api/v1/battles/{battle_id}/queue/ready')
    s2.post(f'/api/v1/battles/{battle_id}/queue/join')
    s2.post(f'/api/v1/battles/{battle_id}/queue/ready')

    # Matchmaking for 2 players respects startup delay; trigger once more after delay.
    time.sleep(1.1)
    s1.post(f'/api/v1/battles/{battle_id}/queue/ready')
    my_room = s1.get(f'/api/v1/battles/{battle_id}/my-room').get_json()
    assert my_room['room_id'] is not None
    room_id = my_room['room_id']
    room = s1.get(f'/api/v1/rooms/{room_id}').get_json()
    match_id = room['match_id']
    assert 'public_tests' in room['task']
    assert isinstance(room['task']['public_tests'], list)
    assert room['task']['public_tests'][0]['expected'] == '3'
    assert room['round']['deadline_at'] is not None
    assert room['round']['seconds_left'] >= 0

    rr = teacher.post(f'/api/v1/matches/{match_id}/rejudge', json={
        'reason': 'manual correction',
        'new_results': [{'student_id': room['participants'][0]['student_id'], 'result_type': 'win'}],
    })
    assert rr.status_code == 400


def test_task_package_import_export(app):
    teacher = app.test_client()
    login_dev(teacher, 'teacher-pkg', 'Teacher', 'teacher')

    payload = {
        'format': 'task-package-v1',
        'name': 'spring-pack',
        'version': '1.0.0',
        'tasks': [
            {
                'title': 'A + B',
                'statement_md': 'sum two ints',
                'difficulty': 'easy',
                'check_type': 'tests',
                'config': {'tests': [{'input': '1 2', 'expected': '3'}]},
            },
            {
                'title': 'Max of three',
                'statement_md': 'print max',
                'difficulty': 'easy',
                'check_type': 'tests',
                'config': {'tests': [{'input': '1 2 3', 'expected': '3'}]},
            },
        ],
    }

    r_import = teacher.post('/api/v1/tasks/import', json=payload)
    assert r_import.status_code == 200
    import_data = r_import.get_json()
    assert len(import_data['created_ids']) == 2
    assert import_data['package']['name'] == 'spring-pack'

    r_export = teacher.get('/api/v1/tasks/export')
    assert r_export.status_code == 200
    export_data = r_export.get_json()
    assert export_data['format'] == 'task-package-v1'
    assert isinstance(export_data['tasks'], list)
    assert len(export_data['tasks']) >= 2


def test_package_crud_and_battle_create_with_packages(app):
    teacher = app.test_client()
    login_dev(teacher, 'teacher-pkg-2', 'Teacher', 'teacher')

    create_pkg = teacher.post('/api/v1/task-packages', json={
        'name': 'Core Pack',
        'description': 'basic tasks',
    })
    assert create_pkg.status_code == 201
    package_id = create_pkg.get_json()['package']['id']

    add_task = teacher.post(f'/api/v1/task-packages/{package_id}/tasks', json={
        'title': 'FizzBuzz',
        'statement_md': 'print from 1..n',
        'difficulty': 'easy',
        'check_type': 'tests',
        'config': {'tests': [{'input': '3', 'expected': '1\\n2\\nFizz'}]},
    })
    assert add_task.status_code == 201
    task_id = add_task.get_json()['id']

    update_task = teacher.patch(f'/api/v1/task-packages/{package_id}/tasks/{task_id}', json={
        'config': {'tests': [{'input': '5', 'expected': '1\\n2\\nFizz\\n4\\nBuzz'}]},
    })
    assert update_task.status_code == 200
    assert 'tests' in update_task.get_json()['config']

    package_details = teacher.get(f'/api/v1/task-packages/{package_id}')
    assert package_details.status_code == 200
    details_data = package_details.get_json()
    assert details_data['package']['name'] == 'Core Pack'
    assert len(details_data['tasks']) == 1

    create_battle = teacher.post('/api/v1/battles', json={
        'title': 'Battle with package',
        'room_size': 2,
        'package_ids': [package_id],
    })
    assert create_battle.status_code == 201
    battle_id = create_battle.get_json()['id']

    battle_packages = teacher.get(f'/api/v1/battles/{battle_id}/task-packages')
    assert battle_packages.status_code == 200
    battle_packages_data = battle_packages.get_json()
    assert len(battle_packages_data) == 1
    assert battle_packages_data[0]['id'] == package_id

    battle_tasks = teacher.get(f'/api/v1/battles/{battle_id}/tasks')
    assert battle_tasks.status_code == 200
    assert len(battle_tasks.get_json()) >= 1


def test_grace_period_and_surrender_flow(app):
    teacher = app.test_client()
    login_dev(teacher, 'teacher-grace', 'Teacher', 'teacher')
    battle_id = create_task_and_battle(teacher)

    s1 = app.test_client()
    s1_user = login_dev(s1, 'grace-s1', 'GraceS1', 'student')
    s2 = app.test_client()
    s2_user = login_dev(s2, 'grace-s2', 'GraceS2', 'student')

    assert s1.post(f'/api/v1/battles/{battle_id}/queue/join').status_code == 200
    assert s1.post(f'/api/v1/battles/{battle_id}/queue/ready').status_code == 200
    assert s2.post(f'/api/v1/battles/{battle_id}/queue/join').status_code == 200
    assert s2.post(f'/api/v1/battles/{battle_id}/queue/ready').status_code == 200

    time.sleep(1.1)
    s1.post(f'/api/v1/battles/{battle_id}/queue/ready')

    my_room = s1.get(f'/api/v1/battles/{battle_id}/my-room').get_json()
    room_id = my_room['room_id']
    assert room_id is not None
    room_before = s1.get(f'/api/v1/rooms/{room_id}').get_json()
    match_id = room_before['match_id']

    submit_r = s1.post(f'/api/v1/rooms/{room_id}/submit', json={
        'language': 'python',
        'source_code': 'print(3)',
    })
    assert submit_r.status_code == 202
    submission_id = submit_r.get_json()['submission_id']

    callback_r = teacher.post('/api/v1/integrations/geekpaste/callback', json={
        'callback_id': submission_id,
        'status': 'success',
        'points': 1,
        'max_points': 1,
        'visible_tests_passed': 1,
        'visible_tests_total': 1,
    })
    assert callback_r.status_code == 200
    s1_room_after_win = s1.get(f'/api/v1/battles/{battle_id}/my-room').get_json()
    assert s1_room_after_win['room_id'] is None

    queue_after_win = teacher.get(f'/api/v1/battles/{battle_id}/queue')
    assert queue_after_win.status_code == 200
    by_user_after_win = {entry['user_id']: entry for entry in queue_after_win.get_json()['entries']}
    assert by_user_after_win[s1_user['id']]['status'] == 'ready'
    assert by_user_after_win[s1_user['id']]['is_fighting'] is False

    room_grace = s2.get(f'/api/v1/rooms/{room_id}').get_json()
    assert room_grace['grace']['winner_student_id'] == s1_user['id']
    assert room_grace['grace']['can_surrender'] is True
    assert room_grace['grace']['is_active'] is True

    surrender_r = s2.post(f'/api/v1/rooms/{room_id}/surrender')
    assert surrender_r.status_code == 200
    assert surrender_r.get_json()['status'] in {'surrendered', 'already_surrendered'}

    match_after = s1.get(f'/api/v1/matches/{match_id}').get_json()
    assert match_after['finished_at'] is not None

    parts_after = s1.get(f'/api/v1/matches/{match_id}/participants').get_json()
    by_user = {p['student_id']: p for p in parts_after}
    assert by_user[s1_user['id']]['result_type'] in {'win', 'draw'}
    assert by_user[s2_user['id']]['result_type'] == 'loss'


def test_matchmaking_pairs_by_rating_and_uses_harder_tasks_for_stronger_group(app):
    from app.extensions import db
    from app.models import User
    from app.utils import as_uuid

    teacher = app.test_client()
    login_dev(teacher, 'teacher-mm', 'TeacherMM', 'teacher')

    battle_id = create_task_and_battle(teacher)

    # Add medium and hard tasks to battle pool.
    for diff, title in [('medium', 'M task'), ('hard', 'H task')]:
        r_task = teacher.post('/api/v1/tasks', json={
            'title': title,
            'statement_md': f'{diff} statement',
            'difficulty': diff,
            'check_type': 'tests',
            'config': {'tests': [{'input': '1 2', 'expected': '3'}]},
        })
        assert r_task.status_code == 201
        task_id = r_task.get_json()['id']
        assert teacher.post(f'/api/v1/battles/{battle_id}/tasks/{task_id}').status_code == 200

    s_hi_1 = app.test_client()
    hi1 = login_dev(s_hi_1, 'hi-1', 'Hi1', 'student')
    s_hi_2 = app.test_client()
    hi2 = login_dev(s_hi_2, 'hi-2', 'Hi2', 'student')
    s_lo_1 = app.test_client()
    lo1 = login_dev(s_lo_1, 'lo-1', 'Lo1', 'student')
    s_lo_2 = app.test_client()
    lo2 = login_dev(s_lo_2, 'lo-2', 'Lo2', 'student')

    with app.app_context():
        ids = [as_uuid(hi1['id']), as_uuid(hi2['id']), as_uuid(lo1['id']), as_uuid(lo2['id'])]
        users = User.query.filter(User.id.in_(ids)).all()
        by_id = {str(u.id): u for u in users}
        by_id[hi1['id']].rating = 1700
        by_id[hi2['id']].rating = 1600
        by_id[lo1['id']].rating = 900
        by_id[lo2['id']].rating = 800
        db.session.commit()

    for c in (s_hi_1, s_hi_2, s_lo_1, s_lo_2):
        assert c.post(f'/api/v1/battles/{battle_id}/queue/join').status_code == 200
        assert c.post(f'/api/v1/battles/{battle_id}/queue/ready').status_code == 200

    time.sleep(1.1)
    # trigger matchmaking pass after delay
    s_hi_1.post(f'/api/v1/battles/{battle_id}/queue/ready')

    room_hi_1 = s_hi_1.get(f'/api/v1/battles/{battle_id}/my-room').get_json()['room_id']
    room_hi_2 = s_hi_2.get(f'/api/v1/battles/{battle_id}/my-room').get_json()['room_id']
    room_lo_1 = s_lo_1.get(f'/api/v1/battles/{battle_id}/my-room').get_json()['room_id']
    room_lo_2 = s_lo_2.get(f'/api/v1/battles/{battle_id}/my-room').get_json()['room_id']

    assert room_hi_1 == room_hi_2
    assert room_lo_1 == room_lo_2
    assert room_hi_1 != room_lo_1

    task_hi = s_hi_1.get(f'/api/v1/rooms/{room_hi_1}').get_json()['task']['difficulty']
    task_lo = s_lo_1.get(f'/api/v1/rooms/{room_lo_1}').get_json()['task']['difficulty']
    assert task_hi in {'hard', 'medium'}
    assert task_lo in {'easy', 'medium'}
    assert {'easy': 0, 'medium': 1, 'hard': 2}[task_hi] >= {'easy': 0, 'medium': 1, 'hard': 2}[task_lo]


def test_round_auto_finishes_when_all_players_disconnected_for_grace(app):
    from app.extensions import db
    from app.models import MatchParticipant
    from app.utils import as_uuid

    teacher = app.test_client()
    login_dev(teacher, 'teacher-disc', 'TeacherDisc', 'teacher')
    battle_id = create_task_and_battle(teacher)

    s1 = app.test_client()
    login_dev(s1, 'disc-s1', 'DiscS1', 'student')
    s2 = app.test_client()
    login_dev(s2, 'disc-s2', 'DiscS2', 'student')

    assert s1.post(f'/api/v1/battles/{battle_id}/queue/join').status_code == 200
    assert s1.post(f'/api/v1/battles/{battle_id}/queue/ready').status_code == 200
    assert s2.post(f'/api/v1/battles/{battle_id}/queue/join').status_code == 200
    assert s2.post(f'/api/v1/battles/{battle_id}/queue/ready').status_code == 200

    time.sleep(1.1)
    s1.post(f'/api/v1/battles/{battle_id}/queue/ready')

    my_room = s1.get(f'/api/v1/battles/{battle_id}/my-room').get_json()
    room_id = my_room['room_id']
    assert room_id is not None

    room_data = s1.get(f'/api/v1/rooms/{room_id}').get_json()
    match_id = room_data['match_id']
    assert match_id is not None

    with app.app_context():
        participants = MatchParticipant.query.filter_by(match_id=as_uuid(match_id)).all()
        assert len(participants) == 2
        offline_since = datetime.now(timezone.utc) - timedelta(seconds=301)
        for participant in participants:
            participant.is_disconnected = True
            participant.disconnected_at = offline_since
        db.session.commit()

    # /battles/<id> triggers tick_timeouts() and should close match as all_disconnected.
    battle_response = teacher.get(f'/api/v1/battles/{battle_id}')
    assert battle_response.status_code == 200

    match_after = s1.get(f'/api/v1/matches/{match_id}').get_json()
    assert match_after['finished_at'] is not None
    assert match_after['finished_by'] == 'all_disconnected'


def test_round_timeout_marks_everyone_as_loss(app):
    from app.extensions import db
    from app.models import Match
    from app.utils import as_uuid

    teacher = app.test_client()
    login_dev(teacher, 'teacher-timeout', 'TeacherTimeout', 'teacher')
    battle_id = create_task_and_battle(teacher)

    s1 = app.test_client()
    s1_user = login_dev(s1, 'timeout-s1', 'TimeoutS1', 'student')
    s2 = app.test_client()
    s2_user = login_dev(s2, 'timeout-s2', 'TimeoutS2', 'student')

    assert s1.post(f'/api/v1/battles/{battle_id}/queue/join').status_code == 200
    assert s1.post(f'/api/v1/battles/{battle_id}/queue/ready').status_code == 200
    assert s2.post(f'/api/v1/battles/{battle_id}/queue/join').status_code == 200
    assert s2.post(f'/api/v1/battles/{battle_id}/queue/ready').status_code == 200

    time.sleep(1.1)
    s1.post(f'/api/v1/battles/{battle_id}/queue/ready')

    my_room = s1.get(f'/api/v1/battles/{battle_id}/my-room').get_json()
    room_id = my_room['room_id']
    assert room_id is not None

    room_data = s1.get(f'/api/v1/rooms/{room_id}').get_json()
    match_id = room_data['match_id']
    assert match_id is not None

    with app.app_context():
        match = db.session.get(Match, as_uuid(match_id))
        assert match is not None
        match.created_at = datetime.now(timezone.utc) - timedelta(minutes=25)
        db.session.commit()

    # /battles/<id> triggers tick_timeouts() and should close the match as timeout.
    battle_response = teacher.get(f'/api/v1/battles/{battle_id}')
    assert battle_response.status_code == 200

    match_after = s1.get(f'/api/v1/matches/{match_id}').get_json()
    assert match_after['finished_at'] is not None
    assert match_after['finished_by'] == 'timeout'

    parts_after = s1.get(f'/api/v1/matches/{match_id}/participants').get_json()
    by_user = {p['student_id']: p for p in parts_after}
    assert by_user[s1_user['id']]['result_type'] == 'loss'
    assert by_user[s2_user['id']]['result_type'] == 'loss'
