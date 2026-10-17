from datetime import datetime, timedelta, timezone
from uuid import UUID

from test_flow import login_dev
from test_reliability import setup_room


def test_personal_place_uses_all_members_and_matches_public_tie_breaks(app):
    _, battle, players, _ = setup_room(app)
    late = app.test_client()
    late_user = login_dev(late, 'standing-member', 'AAA', 'student')
    late.post('/api/v1/battles/join', json={'code': 'B' + battle[:8]})
    report = players[0][0].get(f'/api/v1/me/results/{battle}').get_json()
    context = report['standing']
    assert context['place'] == 2
    assert context['total'] == 3
    assert context['previous_place'] is None and context['change'] is None
    assert context['neighbors'][0]['user_id'] == late_user['id']
    board = players[0][0].get(f'/api/v1/battles/{battle}/leaderboard').get_json()['participants']
    assert [row['user_id'] for row in context['neighbors']] == [row['user_id'] for row in board]
    assert 'tasks' not in str(context)


def test_movement_reconstructs_points_and_elo_before_latest_round(app):
    from app.extensions import db
    from app.models import Room, Match, User, MatchParticipant, BattleMember
    from app.services.scoring_service import finalize_match
    teacher, battle, players, room = setup_room(app)
    a, b = [UUID(player[1]['id']) for player in players]
    start = datetime.now(timezone.utc) - timedelta(minutes=10)
    with app.app_context():
        db.session.get(Room, UUID(room['room_id'])).started_at = start
        for member in BattleMember.query.filter_by(battle_id=UUID(battle)).all():
            member.joined_at = start - timedelta(minutes=1)
        db.session.get(User, a).rating = 900
        db.session.get(User, b).rating = 1100
        # Global season points must not affect this tournament's ordering.
        db.session.get(User, b).season_points = 9000
        part = MatchParticipant.query.filter_by(match_id=UUID(room['match_id']), student_id=a).one()
        part.accepted_at = start + timedelta(minutes=3)
        part.progress = 1
        db.session.commit()
        finalize_match(db.session.get(Match, UUID(room['match_id'])))
    newcomer = app.test_client()
    login_dev(newcomer, 'standing-late', 'Late arrival', 'student')
    newcomer.post('/api/v1/battles/join', json={'code': 'B' + battle[:8]})
    report = players[0][0].get(f'/api/v1/me/results/{battle}').get_json()
    context = report['standing']
    assert (context['place'], context['total'], context['previous_place'], context['change']) == (1, 3, 2, 1)
    assert context['neighbors'][0]['battle_points'] == report['students'][0]['points'] == 140
    assert context['neighbors'][1]['battle_points'] == 30
    assert all(set(row) == {'user_id', 'name', 'place', 'battle_points', 'rating'} for row in context['neighbors'])
    teacher_detail = teacher.get(f"/api/v1/battles/{battle}/students/{players[0][1]['id']}/results").get_json()
    assert teacher_detail['standing'] == context


def test_checked_source_is_available_only_in_own_submission_snapshot(app):
    teacher, _, players, room = setup_room(app)
    path = f"/api/v1/rooms/{room['room_id']}"
    source = 'x = 1\nprint(x / 0)'
    submission = players[0][0].post(path + '/submit', json={'language': 'python', 'source_code': source}).get_json()
    teacher.post('/api/v1/integrations/geekpaste/callback', json={
        'callback_id': submission['submission_id'], 'status': 'error',
        'comment': 'File "main.py", line 2\nZeroDivisionError: division by zero',
    })
    own = players[0][0].get(path).get_json()['my_submission']
    assert (own['source_code'], own['language']) == (source, 'python')
    assert own['created_at'].endswith('+00:00')
    assert source not in str(players[1][0].get(path).get_json())
    assert source not in str(teacher.get(path).get_json())
