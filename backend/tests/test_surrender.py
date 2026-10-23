from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from test_flow import login_dev
from test_reliability import setup_room


def age_room(app, room, seconds=601):
    from app.extensions import db
    from app.models import Room
    with app.app_context():
        db.session.get(Room, UUID(room['room_id'])).started_at = datetime.now(timezone.utc) - timedelta(seconds=seconds)
        db.session.commit()


def accept(teacher, player, room):
    response = player.post(f"/api/v1/rooms/{room['room_id']}/submit", json={'language': 'python', 'source_code': 'print(3)'})
    assert response.status_code == 202
    payload = {'callback_id': response.get_json()['submission_id'], 'status': 'success', 'points': 1, 'max_points': 1}
    assert teacher.post('/api/v1/integrations/geekpaste/callback', json=payload).status_code == 200
    return payload


def test_surrender_unlocks_at_ten_minutes_without_a_winner_and_releases_player(app):
    from app.extensions import db
    from app.models import Match, MatchParticipant, Room, ScoreEvent
    _, battle, players, room = setup_room(app)
    player = players[0][0]
    path = f"/api/v1/rooms/{room['room_id']}"
    outsider = app.test_client()
    login_dev(outsider, 'surrender-outsider', 'Other', 'student')
    assert outsider.post(path + '/surrender').status_code == 403
    age_room(app, room, 599)
    state = player.get(path).get_json()
    assert state['round']['can_surrender'] is False
    assert 'deadline_at' not in state['round']
    assert player.post(path + '/surrender').status_code == 409
    # Exactly the boundary, rather than a rounded number of displayed minutes.
    age_room(app, room, 600)
    assert player.get(path).get_json()['round']['can_surrender'] is True
    assert player.post(path + '/surrender').status_code == 200
    assert player.post(path + '/surrender').get_json()['status'] == 'already_surrendered'
    state = player.get('/api/v1/me/state').get_json()
    assert state['room_id'] is None and state['battle_id'] == battle
    assert state['last_result']['surrendered'] is True
    assert state['last_result']['is_final'] is False
    assert players[1][0].get('/api/v1/me/state').get_json()['room_id'] == room['room_id']
    assert player.post(path + '/submit', json={'language': 'python', 'source_code': 'print(3)'}).status_code == 409
    assert player.post(path + '/runs', json={'language': 'python', 'source_code': 'print(3)'}).status_code == 409
    with app.app_context():
        assert db.session.get(Match, UUID(room['match_id'])).finished_at is None
        assert MatchParticipant.query.filter_by(match_id=UUID(room['match_id']), student_id=UUID(players[0][1]['id'])).one().surrendered_at
        assert ScoreEvent.query.count() == 0  # Surrender alone never awards the opponent a win.


def test_opponent_can_surrender_immediately_after_a_winner_appears(app):
    from app.extensions import db
    from app.models import Match
    teacher, battle, players, room = setup_room(app)
    path = f"/api/v1/rooms/{room['room_id']}"
    loser = players[1][0]
    assert loser.post(path + '/surrender').status_code == 409
    accept(teacher, players[0][0], room)
    state = loser.get(path).get_json()
    assert state['round']['can_surrender'] is True
    assert datetime.fromisoformat(state['round']['surrender_available_at']) <= datetime.fromisoformat(state['round']['server_now'])
    assert players[0][0].post(path + '/surrender').status_code == 409
    assert loser.post(path + '/surrender').status_code == 200
    assert loser.get('/api/v1/me/state').get_json()['room_id'] is None
    with app.app_context():
        assert db.session.get(Match, UUID(room['match_id'])).finished_at is not None


def test_solving_after_surrender_awards_one_bonus_and_replay_preserves_it(app):
    from app.extensions import db
    from app.models import Match, User, ScoreEvent
    from app.services.scoring_service import finalize_match, SURRENDER_BONUS_REASON
    from app.services.score_replay import replay_scores
    teacher, battle, players, room = setup_room(app)
    age_room(app, room)
    assert players[0][0].post(f"/api/v1/rooms/{room['room_id']}/surrender").status_code == 200
    payload = accept(teacher, players[1][0], room)
    assert teacher.post('/api/v1/integrations/geekpaste/callback', json=payload).status_code == 200
    with app.app_context():
        match = db.session.get(Match, UUID(room['match_id']))
        assert match.finished_at is not None
        finalize_match(match)
        winner = db.session.get(User, UUID(players[1][1]['id']))
        assert winner.season_points == 160
        assert winner.win_streak == 1
        events = ScoreEvent.query.filter_by(match_id=match.id, student_id=winner.id, reason=SURRENDER_BONUS_REASON).all()
        assert len(events) == 1 and events[0].points_delta == 20
        replay_scores()
        db.session.commit()
        assert winner.season_points == 160 and winner.win_streak == 1
        assert sum(e.points_delta for e in ScoreEvent.query.filter_by(student_id=winner.id)) == 160
    report = players[1][0].get(f'/api/v1/me/results/{battle}').get_json()
    entries = report['students'][0]['tasks'][0]['score_rounds'][0]['entries']
    assert any(e['reason'] == SURRENDER_BONUS_REASON and e['points'] == 20 for e in entries)
    assert players[1][0].get('/api/v1/me/state').get_json()['last_result']['surrender_bonus'] == 20


def test_surrender_after_opponent_already_solved_does_not_award_bonus(app):
    from app.extensions import db
    from app.models import ScoreEvent
    from app.services.scoring_service import SURRENDER_BONUS_REASON
    teacher, _, players, room = setup_room(app)
    age_room(app, room)
    accept(teacher, players[0][0], room)
    assert players[0][0].post(f"/api/v1/rooms/{room['room_id']}/surrender").status_code == 409
    assert players[1][0].post(f"/api/v1/rooms/{room['room_id']}/surrender").status_code == 200
    with app.app_context():
        assert ScoreEvent.query.filter_by(reason=SURRENDER_BONUS_REASON).count() == 0


def test_all_surrender_is_loss_for_everyone_even_with_different_progress(app):
    from app.extensions import db
    from app.models import Match, MatchParticipant, ScoreEvent
    _, _, players, room = setup_room(app)
    age_room(app, room)
    with app.app_context():
        MatchParticipant.query.filter_by(match_id=UUID(room['match_id']), student_id=UUID(players[0][1]['id'])).one().progress = .5
        db.session.commit()
    for player, _ in players:
        assert player.post(f"/api/v1/rooms/{room['room_id']}/surrender").status_code == 200
    with app.app_context():
        match = db.session.get(Match, UUID(room['match_id']))
        assert match.finished_by == 'surrendered'
        assert {p.result_type for p in MatchParticipant.query.filter_by(match_id=match.id)} == {'loss'}
        assert sorted(e.points_delta for e in ScoreEvent.query.all()) == [30, 50]


def test_pending_callback_does_not_resurrect_surrendered_player(app):
    from app.extensions import db
    from app.models import MatchParticipant, ScoreEvent
    teacher, _, players, room = setup_room(app)
    age_room(app, room)
    response = players[0][0].post(f"/api/v1/rooms/{room['room_id']}/submit", json={'language': 'python', 'source_code': 'print(3)'})
    assert players[0][0].post(f"/api/v1/rooms/{room['room_id']}/surrender").status_code == 200
    teacher.post('/api/v1/integrations/geekpaste/callback', json={
        'callback_id': response.get_json()['submission_id'], 'status': 'success', 'points': 1, 'max_points': 1,
    })
    with app.app_context():
        p = MatchParticipant.query.filter_by(match_id=UUID(room['match_id']), student_id=UUID(players[0][1]['id'])).one()
        assert p.accepted_at is None and float(p.progress or 0) == 0
        assert p.result_type == 'loss' and ScoreEvent.query.count() == 0


def test_multiple_surrendered_opponents_give_only_one_bonus(app):
    from app.extensions import db
    from app.models import MatchParticipant, ScoreEvent
    from app.services.scoring_service import SURRENDER_BONUS_REASON
    teacher, _, players, room = setup_room(app)
    third = app.test_client()
    user = login_dev(third, 'third-player', 'Third', 'student')
    with app.app_context():
        db.session.add(MatchParticipant(match_id=UUID(room['match_id']), student_id=UUID(user['id'])))
        db.session.commit()
    age_room(app, room)
    for player in [players[0][0], third]:
        assert player.post(f"/api/v1/rooms/{room['room_id']}/surrender").status_code == 200
    accept(teacher, players[1][0], room)
    with app.app_context():
        bonuses = ScoreEvent.query.filter_by(reason=SURRENDER_BONUS_REASON).all()
        assert len(bonuses) == 1 and bonuses[0].points_delta == 20


def test_simultaneous_first_solutions_do_not_end_a_third_players_round(app):
    from app.extensions import db
    from app.models import MatchParticipant, Match
    teacher, battle, players, room = setup_room(app)
    third = app.test_client()
    user = login_dev(third, 'third-player', 'Third', 'student')
    with app.app_context():
        for p in MatchParticipant.query.filter_by(match_id=UUID(room['match_id'])):
            p.accepted_at = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=1)
        db.session.add(MatchParticipant(match_id=UUID(room['match_id']), student_id=UUID(user['id'])))
        db.session.commit()
    teacher.get(f'/api/v1/battles/{battle}')
    with app.app_context():
        assert db.session.get(Match, UUID(room['match_id'])).finished_at is None
    assert third.get(f"/api/v1/rooms/{room['room_id']}").get_json()['round']['is_active'] is True


def test_long_round_still_allows_practice_and_submission(app):
    teacher, battle, players, room = setup_room(app)
    age_room(app, room, 24 * 3600)
    assert teacher.get(f'/api/v1/battles/{battle}').status_code == 200
    assert players[0][0].post(f"/api/v1/rooms/{room['room_id']}/runs", json={'language': 'python', 'source_code': 'print(3)'}).status_code == 202
    accept(teacher, players[0][0], room)
    assert players[1][0].get(f"/api/v1/rooms/{room['room_id']}").get_json()['round']['is_active'] is True


def test_surrender_migration_preserves_legacy_marker_and_is_reversible(app):
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect, text
    from app.extensions import db
    _, _, _, room = setup_room(app)
    path = Path(__file__).parents[1] / 'migrations/versions/0007_surrender.py'
    spec = importlib.util.spec_from_file_location('surrender_migration', path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with app.app_context(), db.engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
            connection.execute(text("UPDATE match_participants SET result_type = 'loss'"))
            migration.upgrade()
            assert 'surrendered_at' in {c['name'] for c in inspect(connection).get_columns('match_participants')}
            assert connection.execute(text('SELECT count(*) FROM match_participants WHERE surrendered_at IS NOT NULL')).scalar() == 2
            migration.downgrade()
            assert 'surrendered_at' not in {c['name'] for c in inspect(connection).get_columns('match_participants')}
            migration.upgrade()


@pytest.mark.parametrize('new_room', [False, True])
def test_older_round_finishing_preserves_surrendered_players_next_state(app, new_room):
    from app.extensions import db
    from app.models import QueueEntry, Match, Room, MatchParticipant
    teacher, battle, players, room = setup_room(app)
    age_room(app, room)
    student_id = UUID(players[0][1]['id'])
    players[0][0].post(f"/api/v1/rooms/{room['room_id']}/surrender")
    with app.app_context():
        queue = QueueEntry.query.filter_by(user_id=student_id).one()
        if new_room:
            db.session.delete(queue)
            next_room = Room(battle_id=UUID(battle), status='active', started_at=datetime.now(timezone.utc))
            db.session.add(next_room)
            db.session.flush()
            next_match = Match(room_id=next_room.id, task_id=db.session.get(Match, UUID(room['match_id'])).task_id)
            db.session.add(next_match)
            db.session.flush()
            db.session.add(MatchParticipant(match_id=next_match.id, student_id=student_id))
        else:
            queue.is_ready = True
        db.session.commit()
    accept(teacher, players[1][0], room)
    with app.app_context():
        queue = QueueEntry.query.filter_by(user_id=student_id).first()
        assert queue is None if new_room else queue.is_ready is True
