from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from test_reliability import setup_room


CALLBACK = '/api/v1/integrations/geekpaste/callback'


def timed_out_submission(app):
    from app.extensions import db
    from app.models import Submission
    from app.services.rooms_service import expire_stale_submissions
    app.config['SUBMISSION_CHECK_TIMEOUT_SECONDS'] = 2
    teacher, battle, players, room = setup_room(app)
    response = players[0][0].post(f"/api/v1/rooms/{room['room_id']}/submit", json={
        'language': 'cpp', 'source_code': 'int main() {}',
    })
    assert response.status_code == 202
    submission_id = response.get_json()['submission_id']
    with app.app_context():
        submission = db.session.get(Submission, UUID(submission_id))
        submission.created_at = datetime.now(timezone.utc) - timedelta(seconds=3)
        db.session.commit()
        assert expire_stale_submissions(room['match_id']) == 1
    payload = {'callback_id': submission_id, 'job_id': submission_id,
               'status': 'success', 'points': 1, 'max_points': 1}
    return teacher, battle, players, room, payload


@pytest.mark.parametrize('job_id', [None, 'another-job'])
def test_timeout_rejects_missing_or_mismatched_job(app, job_id):
    from app.extensions import db
    from app.models import Submission, ScoreEvent
    teacher, _, _, _, payload = timed_out_submission(app)
    payload['job_id'] = job_id
    assert teacher.post(CALLBACK, json=payload).status_code == 200
    with app.app_context():
        assert db.session.get(Submission, UUID(payload['callback_id'])).verdict == 'internal_error'
        assert ScoreEvent.query.count() == 0


def test_late_acceptance_after_resubmit_awards_points_once(app):
    from app.extensions import db
    from app.models import Submission, MatchParticipant, ScoreEvent, User
    teacher, _, players, room, payload = timed_out_submission(app)
    # A newer retry must not suppress a genuine result of the older job.
    newer = players[0][0].post(f"/api/v1/rooms/{room['room_id']}/submit", json={
        'language': 'cpp', 'source_code': 'int main() {}',
    }).get_json()['submission_id']
    assert teacher.post(CALLBACK, json=payload).status_code == 200
    assert teacher.post(CALLBACK, json=payload).status_code == 200
    assert teacher.post(CALLBACK, json={**payload, 'callback_id': newer, 'job_id': newer}).status_code == 200
    with app.app_context():
        assert db.session.get(Submission, UUID(payload['callback_id'])).verdict == 'accepted'
        participant = MatchParticipant.query.filter_by(
            match_id=UUID(room['match_id']), student_id=UUID(players[0][1]['id'])).one()
        assert participant.accepted_at is not None
        assert float(participant.progress) == 1
        assert ScoreEvent.query.count() == 1
        assert db.session.get(User, participant.student_id).season_points == 140


def test_late_result_of_closed_round_is_saved_without_changing_scores(app):
    from app.extensions import db
    from app.models import Submission, MatchParticipant, ScoreEvent, Match
    from app.services.scoring_service import finalize_match
    teacher, _, _, room, payload = timed_out_submission(app)
    with app.app_context():
        match = db.session.get(Match, UUID(room['match_id']))
        finalize_match(match, finished_by='battle_stopped')
        before = [(str(p.student_id), p.result_type, p.accepted_at) for p in
                  MatchParticipant.query.filter_by(match_id=match.id).order_by(MatchParticipant.student_id)]
        score_ids = [str(event.id) for event in ScoreEvent.query.all()]
    assert teacher.post(CALLBACK, json=payload).status_code == 200
    with app.app_context():
        assert db.session.get(Submission, UUID(payload['callback_id'])).verdict == 'accepted'
        after = [(str(p.student_id), p.result_type, p.accepted_at) for p in
                 MatchParticipant.query.filter_by(match_id=UUID(room['match_id'])).order_by(MatchParticipant.student_id)]
        assert before == after
        assert score_ids == [str(event.id) for event in ScoreEvent.query.all()]


def test_callback_cannot_replace_a_terminal_checker_error(app):
    from app.extensions import db
    from app.models import Submission
    teacher, _, _, _, payload = timed_out_submission(app)
    with app.app_context():
        submission = db.session.get(Submission, UUID(payload['callback_id']))
        submission.checker_status_raw = 'error'
        db.session.commit()
    assert teacher.post(CALLBACK, json=payload).status_code == 200
    with app.app_context():
        assert db.session.get(Submission, UUID(payload['callback_id'])).verdict == 'internal_error'


def test_queued_submission_rejects_mismatched_job(app):
    from app.extensions import db
    from app.models import Submission
    teacher, _, _, _, payload = timed_out_submission(app)
    with app.app_context():
        db.session.get(Submission, UUID(payload['callback_id'])).verdict = 'queued'
        db.session.commit()
    assert teacher.post(CALLBACK, json={**payload, 'job_id': 'another-job'}).status_code == 200
    with app.app_context():
        assert db.session.get(Submission, UUID(payload['callback_id'])).verdict == 'queued'


def test_practice_run_can_recover_its_matching_late_result(app):
    from app.extensions import db
    from app.models import CodeRun, ScoreEvent
    teacher, _, players, room = setup_room(app)
    app.config['SUBMISSION_CHECK_TIMEOUT_SECONDS'] = 2
    path = f"/api/v1/rooms/{room['room_id']}/runs"
    response = players[0][0].post(path, json={
        'language': 'cpp', 'source_code': 'int main() {}', 'kind': 'custom', 'input': '39',
    })
    assert response.status_code == 202
    run_id = response.get_json()['id']
    with app.app_context():
        db.session.get(CodeRun, UUID(run_id)).created_at = datetime.now(timezone.utc) - timedelta(seconds=3)
        db.session.commit()
    assert players[0][0].get(f'{path}/{run_id}').get_json()['verdict'] == 'internal_error'
    endpoint = '/api/v1/integrations/geekpaste/run-callback'
    payload = {'callback_id': run_id, 'job_id': run_id, 'status': 'success', 'points': 1, 'max_points': 1}
    assert teacher.post(endpoint, json={**payload, 'job_id': 'wrong'}).status_code == 200
    assert players[0][0].get(f'{path}/{run_id}').get_json()['verdict'] == 'internal_error'
    assert teacher.post(endpoint, json=payload).status_code == 200
    assert players[0][0].get(f'{path}/{run_id}').get_json()['verdict'] == 'completed'
    with app.app_context():
        assert ScoreEvent.query.count() == 0
