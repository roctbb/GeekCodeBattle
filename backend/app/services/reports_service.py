"""Battle-level progress and personal solution history. Never expose checker configuration."""
from collections import defaultdict
from sqlalchemy.orm import load_only
import json

from ..extensions import db
from ..models import (Battle, BattleMember, BattleTask, Task, Match, MatchParticipant,
                      Room, Submission, User, ScoreEvent, RatingHistory)
from ..api.serializers import battle_out
from .test_visibility import task_tests, is_hidden, public_test, public_snapshot, has_hidden_tests, hidden_test_feedback


def public_task(task):
    tests = task_tests(task)
    return {'id': str(task.id), 'title': task.title, 'difficulty': task.difficulty,
            'statement_md': task.statement_md,
            'public_tests': [public_test(t) for t in tests if isinstance(t, dict) and not is_hidden(t)]}


def _iso(value):
    return value.isoformat() if value else None


def submission_out(sub, match, task=None):
    # Comments are shown as text. Structured checker test details can contain hidden tests.
    comment = sub.checker_comment_raw
    if comment:
        try:
            parsed = json.loads(comment)
            comment = parsed.get('comment') if isinstance(parsed, dict) else None
        except (ValueError, TypeError):
            pass
        if not isinstance(comment, str):
            comment = None
    if has_hidden_tests(task):
        comment = hidden_test_feedback(sub)
    return {'id': str(sub.id), 'match_id': str(sub.match_id), 'created_at': _iso(sub.created_at),
            'language': sub.language, 'source_code': sub.source_code, 'verdict': sub.verdict,
            'progress': float(sub.progress_value or 0), 'comment': (comment or '')[:4000],
            'visible_tests_passed': sub.visible_tests_passed, 'visible_tests_total': sub.visible_tests_total,
            'round_finished_at': _iso(match.finished_at),
            'after_round': bool(match.finished_at and sub.created_at > match.finished_at)}


def battle_report(battle, *, user_id=None, detail=False):
    """Bounded query count for the matrix; only one student's detail contains source code."""
    members = db.session.query(BattleMember, User).join(User).filter(BattleMember.battle_id == battle.id)
    if user_id:
        members = members.filter(BattleMember.user_id == user_id)
    members = members.order_by(User.name, User.id).all()
    selected_ids = {u.id for _, u in members}
    matches = {m.id: m for m in Match.query.join(Room).filter(Room.battle_id == battle.id).order_by(Match.created_at).all()}
    participants = MatchParticipant.query.filter(MatchParticipant.match_id.in_(matches), MatchParticipant.student_id.in_(selected_ids)).all()
    parts = defaultdict(list)
    for p in participants:
        parts[(p.student_id, matches[p.match_id].task_id)].append(p)
    assigned_ids = {matches[p.match_id].task_id for p in participants}
    owned_match_ids = {p.match_id for p in participants}
    pool = Task.query.join(BattleTask).filter(BattleTask.battle_id == battle.id).order_by(Task.created_at, Task.id).all()
    current_tasks = {t.id: t for t in pool}
    missing_ids = {m.task_id for m in matches.values()} - current_tasks.keys()
    if missing_ids:
        current_tasks.update({t.id: t for t in Task.query.filter(Task.id.in_(missing_ids)).all()})
    all_tasks = {t.id: public_task(t) for t in pool}
    # Use the condition issued in the round, even if the teacher later edits/removes the task.
    for match in matches.values():
        if user_id and match.id not in owned_match_ids:
            continue
        if match.task_snapshot:
            all_tasks[match.task_id] = public_snapshot(match.task_snapshot, current_tasks.get(match.task_id))
        elif match.task_id not in all_tasks:
            task = db.session.get(Task, match.task_id)
            if task:
                all_tasks[task.id] = public_task(task)
    if user_id and battle.status not in {'stopped', 'finished'}:
        all_tasks = {tid: t for tid, t in all_tasks.items() if tid in assigned_ids}
    submissions_query = Submission.query.filter(Submission.match_id.in_(matches), Submission.student_id.in_(selected_ids)).order_by(Submission.created_at.desc(), Submission.id)
    if not detail:
        submissions_query = submissions_query.options(load_only(Submission.id, Submission.match_id, Submission.student_id, Submission.verdict, Submission.progress_value))
    submissions = submissions_query.all()
    subs = defaultdict(list)
    for sub in submissions:
        subs[(sub.student_id, matches[sub.match_id].task_id)].append(sub)
    points, ratings = defaultdict(int), defaultdict(int)
    for e in ScoreEvent.query.filter(ScoreEvent.match_id.in_(matches), ScoreEvent.student_id.in_(selected_ids)).all():
        points[e.student_id] += e.points_delta
    for h in RatingHistory.query.filter(RatingHistory.match_id.in_(matches), RatingHistory.user_id.in_(selected_ids)).all():
        ratings[h.user_id] += h.new_rating - h.old_rating
    rows = []
    for member, user in members:
        tasks = []
        for tid, task in all_tasks.items():
            ps, ss = parts[(user.id, tid)], subs[(user.id, tid)]
            solved = any(p.accepted_at for p in ps) or any(s.verdict == 'accepted' for s in ss)
            state = 'solved' if solved else 'attempted' if ss else 'unattempted' if ps else 'not_assigned'
            row = {'task_id': str(tid), 'title': task['title'], 'state': state, 'assigned': bool(ps),
                   'attempts': len(ss), 'accepted': sum(s.verdict == 'accepted' for s in ss),
                   'pending': sum(s.verdict == 'queued' for s in ss),
                   'progress': max([float(p.progress or 0) for p in ps] + [float(s.progress_value or 0) for s in ss] + [0]),
                   'rounds': len(ps)}
            if detail:
                row.update({'statement_md': task.get('statement_md', ''), 'difficulty': task.get('difficulty'),
                            'public_tests': task.get('public_tests', []),
                            'submissions': [submission_out(s, matches[s.match_id], current_tasks.get(tid)) for s in ss]})
            tasks.append(row)
        assigned = sum(t['assigned'] for t in tasks)
        solved = sum(t['state'] == 'solved' for t in tasks)
        rows.append({'user_id': str(user.id), 'name': user.name, 'joined_at': _iso(member.joined_at),
                     'points': points[user.id], 'rating_delta': ratings[user.id], 'rating': user.rating,
                     'solved': solved, 'assigned': assigned, 'unsolved': assigned - solved,
                     'not_assigned': len(tasks) - assigned, 'attempts': sum(t['attempts'] for t in tasks),
                     'pending': sum(t['pending'] for t in tasks), 'tasks': tasks})
    rows.sort(key=lambda r: (-r['points'], -r['rating'], r['name'], r['user_id']))
    for index, row in enumerate(rows, 1):
        row['place'] = index
    return {'battle': battle_out(battle),
            'tasks': [{'id': str(tid), 'title': t['title']} for tid, t in all_tasks.items()],
            'students': rows,
            'summary': {'participants': len(rows), 'tasks': len(all_tasks),
                        'solved': sum(r['solved'] for r in rows), 'attempts': sum(r['attempts'] for r in rows),
                        'pending': sum(r['pending'] for r in rows)}}


def my_results(user):
    admissions = db.session.query(BattleMember, Battle).join(Battle).filter(BattleMember.user_id == user.id).order_by(Battle.created_at.desc()).all()
    assigned, solved = defaultdict(set), defaultdict(set)
    attempts, pending, points, ratings = defaultdict(int), defaultdict(int), defaultdict(int), defaultdict(int)
    for bid, tid, accepted in db.session.query(Room.battle_id, Match.task_id, MatchParticipant.accepted_at).select_from(MatchParticipant).join(Match).join(Room).filter(MatchParticipant.student_id == user.id).all():
        assigned[bid].add(tid)
        if accepted:
            solved[bid].add(tid)
    for bid, tid, verdict in db.session.query(Room.battle_id, Match.task_id, Submission.verdict).select_from(Submission).join(Match).join(Room).filter(Submission.student_id == user.id).all():
        attempts[bid] += 1
        pending[bid] += verdict == 'queued'
        if verdict == 'accepted':
            solved[bid].add(tid)
    for bid, total in db.session.query(Room.battle_id, db.func.sum(ScoreEvent.points_delta)).select_from(ScoreEvent).join(Match).join(Room).filter(ScoreEvent.student_id == user.id).group_by(Room.battle_id).all():
        points[bid] = int(total or 0)
    for bid, total in db.session.query(Room.battle_id, db.func.sum(RatingHistory.new_rating - RatingHistory.old_rating)).select_from(RatingHistory).join(Match).join(Room).filter(RatingHistory.user_id == user.id).group_by(Room.battle_id).all():
        ratings[bid] = int(total or 0)
    return [{'battle': battle_out(b), 'joined_at': _iso(m.joined_at),
             'assigned': len(assigned[b.id]), 'solved': len(solved[b.id]),
             'unsolved': len(assigned[b.id] - solved[b.id]), 'attempts': attempts[b.id],
             'pending': pending[b.id], 'points': points[b.id], 'rating_delta': ratings[b.id]}
            for m, b in admissions]
