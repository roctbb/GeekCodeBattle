from datetime import datetime, timezone
from uuid import UUID

from test_flow import create_task_and_battle
from test_reliability import setup_room


def new_round(app, battle_id, task_id, players):
    from app.extensions import db
    from app.models import Room, Match, MatchParticipant, BattleMember
    with app.app_context():
        for _, user in players:
            if not BattleMember.query.filter_by(battle_id=UUID(battle_id), user_id=UUID(user['id'])).first():
                db.session.add(BattleMember(battle_id=UUID(battle_id), user_id=UUID(user['id'])))
        room = Room(battle_id=UUID(battle_id), status='active', started_at=datetime.now(timezone.utc))
        db.session.add(room)
        db.session.flush()
        match = Match(room_id=room.id, task_id=task_id)
        db.session.add(match)
        db.session.flush()
        db.session.add_all([MatchParticipant(match_id=match.id, student_id=UUID(user['id'])) for _, user in players])
        db.session.commit()
        return str(match.id)


def win_round(app, match_id, winner_id):
    from app.extensions import db
    from app.models import Match, MatchParticipant
    from app.services.scoring_service import award_instant_winner_points, finalize_match
    with app.app_context():
        winner = MatchParticipant.query.filter_by(match_id=UUID(match_id), student_id=UUID(winner_id)).one()
        winner.accepted_at = datetime.now(timezone.utc)
        winner.progress = 1
        db.session.commit()
        match = db.session.get(Match, UUID(match_id))
        delta = award_instant_winner_points(match, winner.student_id)
        finalize_match(match)
        return delta


def test_new_battle_has_zero_streak_and_no_bonus_from_previous_battle(app):
    from app.extensions import db
    from app.models import Match
    from app.services.score_replay import replay_scores
    teacher, battle_a, players, room = setup_room(app)
    winner_id = players[0][1]['id']
    with app.app_context():
        task_id = db.session.get(Match, UUID(room['match_id'])).task_id
    assert win_round(app, room['match_id'], winner_id) == 140
    second = new_round(app, battle_a, task_id, players)
    assert win_round(app, second, winner_id) == 150

    battle_b = create_task_and_battle(teacher)
    first_in_b = new_round(app, battle_b, task_id, players)
    state = players[0][0].get('/api/v1/me/state').get_json()
    assert state['battle_id'] == battle_b
    assert state['me']['win_streak'] == state['me']['loss_streak'] == 0
    assert win_round(app, first_in_b, winner_id) == 140
    for battle_id, expected in [(battle_a, 2), (battle_b, 1)]:
        board = players[0][0].get(f'/api/v1/battles/{battle_id}/leaderboard').get_json()['participants']
        assert next(row for row in board if row['user_id'] == winner_id)['win_streak'] == expected
    with app.app_context():
        from app.services.streaks import battle_streaks
        assert battle_streaks(battle_a, [UUID(winner_id)])[UUID(winner_id)].win_streak == 2
        assert battle_streaks(battle_b, [UUID(winner_id)])[UUID(winner_id)].win_streak == 1
        replay_scores()
        db.session.commit()
        from app.models import ScoreEvent
        assert sum(event.points_delta for event in ScoreEvent.query.filter_by(match_id=UUID(first_in_b), student_id=UUID(winner_id))) == 140


def test_interleaved_battles_keep_independent_streaks_and_rejudge_bonuses(app):
    from app.extensions import db
    from app.models import Match, ScoreEvent
    from app.services.streaks import battle_streaks
    teacher, battle_a, players, room = setup_room(app)
    winner_id, other_id = [user['id'] for _, user in players]
    with app.app_context():
        task_id = db.session.get(Match, UUID(room['match_id'])).task_id
    assert win_round(app, room['match_id'], winner_id) == 140
    battle_b = create_task_and_battle(teacher)
    b_match = new_round(app, battle_b, task_id, players)
    assert win_round(app, b_match, winner_id) == 140
    a_match = new_round(app, battle_a, task_id, players)
    assert win_round(app, a_match, winner_id) == 150
    assert teacher.post(f"/api/v1/matches/{room['match_id']}/rejudge", json={
        'reason': 'Correct the first round', 'new_results': [
            {'student_id': winner_id, 'result_type': 'loss'}, {'student_id': other_id, 'result_type': 'win'},
        ],
    }).status_code == 200
    with app.app_context():
        assert battle_streaks(battle_a, [UUID(winner_id)])[UUID(winner_id)].win_streak == 1
        assert battle_streaks(battle_b, [UUID(winner_id)])[UUID(winner_id)].win_streak == 1
        for match_id in (a_match, b_match):
            assert sum(event.points_delta for event in ScoreEvent.query.filter_by(match_id=UUID(match_id), student_id=UUID(winner_id))) == 140
