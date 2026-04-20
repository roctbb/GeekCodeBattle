from datetime import datetime, timezone, timedelta
from flask import current_app

from ..extensions import db
from ..models import (
    Battle,
    Room,
    Match,
    MatchParticipant,
    BattleTask,
    Task,
    TaskPackage,
    TaskPackageTask,
    BattleTaskPackage,
    QueueEntry,
    Submission,
    ScoreEvent,
    RatingHistory,
    User,
)
from ..utils import as_uuid
from .scoring_service import finalize_match
from .scoring_service import try_finalize_after_submission, get_winner_info
from . import rooms_service
from . import realtime_service


def list_battles():
    return Battle.query.order_by(Battle.created_at.desc()).all()


def list_running_battles():
    return Battle.query.filter_by(status="running").all()


def list_battle_tasks(battle_id):
    rows = (
        db.session.query(Task)
        .join(BattleTask, BattleTask.task_id == Task.id)
        .filter(BattleTask.battle_id == battle_id)
        .order_by(Task.created_at.desc())
        .all()
    )
    return rows


def list_battle_task_packages(battle_id):
    return (
        db.session.query(TaskPackage)
        .join(BattleTaskPackage, BattleTaskPackage.package_id == TaskPackage.id)
        .filter(BattleTaskPackage.battle_id == as_uuid(battle_id))
        .order_by(TaskPackage.created_at.desc())
        .all()
    )


def add_task_to_battle(battle, task_id):
    task = db.session.get(Task, as_uuid(task_id))
    if not task:
        return None, "task_not_found"
    existing = BattleTask.query.filter_by(battle_id=battle.id, task_id=task.id).first()
    if existing:
        return task, None
    db.session.add(BattleTask(battle_id=battle.id, task_id=task.id))
    db.session.commit()
    return task, None


def add_task_package_to_battle(battle, package_id):
    package = db.session.get(TaskPackage, as_uuid(package_id))
    if not package:
        return None, "package_not_found"

    existing_package_rel = BattleTaskPackage.query.filter_by(battle_id=battle.id, package_id=package.id).first()
    if not existing_package_rel:
        db.session.add(BattleTaskPackage(battle_id=battle.id, package_id=package.id))

    package_task_ids = (
        db.session.query(TaskPackageTask.task_id)
        .filter(TaskPackageTask.package_id == package.id)
        .all()
    )
    for (task_id,) in package_task_ids:
        exists = BattleTask.query.filter_by(battle_id=battle.id, task_id=task_id).first()
        if not exists:
            db.session.add(BattleTask(battle_id=battle.id, task_id=task_id))

    db.session.commit()
    return package, None


def remove_task_package_from_battle(battle, package_id):
    rel = BattleTaskPackage.query.filter_by(battle_id=battle.id, package_id=as_uuid(package_id)).first()
    if not rel:
        return False
    db.session.delete(rel)
    db.session.commit()
    return True


def remove_task_from_battle(battle, task_id):
    rel = BattleTask.query.filter_by(battle_id=battle.id, task_id=as_uuid(task_id)).first()
    if not rel:
        return False
    db.session.delete(rel)
    db.session.commit()
    return True


def get_battle_or_none(battle_id):
    return db.session.get(Battle, as_uuid(battle_id))


def create_battle(*, title: str, created_by, room_size: int = 2, package_ids=None):
    battle = Battle(title=title, room_size=int(room_size), created_by=as_uuid(created_by), status="draft")
    db.session.add(battle)
    db.session.commit()

    for package_id in package_ids or []:
        add_task_package_to_battle(battle, package_id)

    return battle


def update_battle(battle, *, title=None):
    if title is not None:
        battle.title = title
    db.session.commit()
    return battle


def open_lobby(battle):
    battle.status = "lobby_open"
    db.session.commit()
    return battle


def start_battle(battle):
    battle.status = "running"
    battle.started_at = datetime.now(timezone.utc)
    db.session.commit()
    return battle


def stop_battle(battle):
    battle.status = "stopped"
    active_rooms = Room.query.filter_by(battle_id=battle.id, status="active").all()
    for room in active_rooms:
        match = Match.query.filter_by(room_id=room.id, finished_at=None).first()
        if match:
            finalize_match(match, finished_by="teacher_stop")
        else:
            room.status = "finished"
            room.finished_at = datetime.now(timezone.utc)
    db.session.commit()
    return battle


def finish_battle(battle):
    stop_battle(battle)
    battle.status = "finished"
    battle.finished_at = datetime.now(timezone.utc)
    db.session.commit()
    return battle


def delete_finished_battle(battle):
    if battle.status != "finished":
        return False, "battle_not_finished"

    room_ids = (
        db.session.query(Room.id)
        .filter(Room.battle_id == battle.id)
        .all()
    )
    room_ids = [room_id for (room_id,) in room_ids]

    match_ids = []
    if room_ids:
        match_rows = (
            db.session.query(Match.id)
            .filter(Match.room_id.in_(room_ids))
            .all()
        )
        match_ids = [match_id for (match_id,) in match_rows]

    if match_ids:
        db.session.query(Submission).filter(Submission.match_id.in_(match_ids)).delete(synchronize_session=False)
        db.session.query(MatchParticipant).filter(MatchParticipant.match_id.in_(match_ids)).delete(synchronize_session=False)
        db.session.query(ScoreEvent).filter(ScoreEvent.match_id.in_(match_ids)).delete(synchronize_session=False)
        db.session.query(RatingHistory).filter(RatingHistory.match_id.in_(match_ids)).delete(synchronize_session=False)
        db.session.query(Match).filter(Match.id.in_(match_ids)).delete(synchronize_session=False)

    if room_ids:
        db.session.query(Room).filter(Room.id.in_(room_ids)).delete(synchronize_session=False)

    db.session.query(QueueEntry).filter(QueueEntry.battle_id == battle.id).delete(synchronize_session=False)
    db.session.query(BattleTask).filter(BattleTask.battle_id == battle.id).delete(synchronize_session=False)
    db.session.query(BattleTaskPackage).filter(BattleTaskPackage.battle_id == battle.id).delete(synchronize_session=False)
    db.session.delete(battle)
    db.session.commit()
    return True, None


def tick_timeouts(battle):
    if battle.status != "running":
        return 0
    limit = timedelta(minutes=current_app.config.get("ROUND_DURATION_MINUTES", 20))
    disconnect_grace = timedelta(seconds=int(current_app.config.get("DISCONNECT_GRACE_SECONDS", 300)))
    now = datetime.now(timezone.utc)
    active_matches = (
        db.session.query(Match)
        .join(Room, Room.id == Match.room_id)
        .filter(Room.battle_id == battle.id, Match.finished_at.is_(None))
        .all()
    )
    finalized_count = 0
    finalized_match_ids = []
    for match in active_matches:
        rooms_service.expire_stale_submissions(match.id, battle_id=battle.id)

        participants = MatchParticipant.query.filter_by(match_id=match.id).all()
        if participants and all(bool(p.is_disconnected) for p in participants):
            last_disconnect_at = max(
                (
                    (p.disconnected_at.replace(tzinfo=timezone.utc) if p.disconnected_at and p.disconnected_at.tzinfo is None else p.disconnected_at)
                    or now
                )
                for p in participants
            )
            if last_disconnect_at <= now - disconnect_grace:
                finalize_match(match, finished_by="all_disconnected")
                finalized_count += 1
                finalized_match_ids.append((match.id, "all_disconnected"))
                continue

        winner, _, _ = get_winner_info(participants)
        if winner is not None:
            if try_finalize_after_submission(match):
                db.session.refresh(match)
                finalized_count += 1
                finalized_match_ids.append((match.id, match.finished_by or "accepted"))
            continue

        match_created_at = match.created_at
        if match_created_at is not None and match_created_at.tzinfo is None:
            match_created_at = match_created_at.replace(tzinfo=timezone.utc)
        if match_created_at is not None and match_created_at <= now - limit:
            finalize_match(match, finished_by="timeout")
            finalized_count += 1
            finalized_match_ids.append((match.id, "timeout"))

    from . import realtime_service, matchmaker_service
    if finalized_match_ids:
        realtime_service.emit_leaderboard_updated(battle.id)
        realtime_service.emit_queue_updated(battle.id, {"battle_id": str(battle.id)})
        for match_id, finished_by in finalized_match_ids:
            realtime_service.emit_round_finished(match_id, finished_by)
    created_rooms = matchmaker_service.run_matchmaking(battle.id)
    if created_rooms:
        if not finalized_match_ids:
            realtime_service.emit_queue_updated(battle.id, {"battle_id": str(battle.id)})
        for room_info in created_rooms:
            realtime_service.emit_match_found(room_info)

    return finalized_count


def list_battle_logs(battle_id):
    battle_uuid = as_uuid(battle_id)
    participant_rows = (
        db.session.query(MatchParticipant, User, Match, Room, Task)
        .join(User, User.id == MatchParticipant.student_id)
        .join(Match, Match.id == MatchParticipant.match_id)
        .join(Room, Room.id == Match.room_id)
        .join(Task, Task.id == Match.task_id)
        .filter(Room.battle_id == battle_uuid)
        .order_by(Match.created_at.desc(), User.name.asc())
        .all()
    )

    submissions = (
        db.session.query(Submission)
        .join(Match, Match.id == Submission.match_id)
        .join(Room, Room.id == Match.room_id)
        .filter(Room.battle_id == battle_uuid)
        .order_by(Submission.created_at.desc())
        .all()
    )
    submissions_by_key = {}
    for sub in submissions:
        key = (sub.match_id, sub.student_id)
        submissions_by_key.setdefault(key, []).append(sub)

    def _sub_out(item):
        if not item:
            return None
        return {
            "id": str(item.id),
            "language": item.language,
            "verdict": item.verdict,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "visible_tests_passed": item.visible_tests_passed,
            "visible_tests_total": item.visible_tests_total,
        }

    logs = []
    for participant, user, match, room, task in participant_rows:
        student_submissions = submissions_by_key.get((match.id, participant.student_id), [])
        latest_submission = student_submissions[0] if student_submissions else None
        final_submission = next((s for s in student_submissions if s.verdict == "accepted"), None) or latest_submission

        logs.append(
            {
                "room_id": str(room.id),
                "match_id": str(match.id),
                "task": {"id": str(task.id), "title": task.title, "difficulty": task.difficulty},
                "student": {"id": str(user.id), "name": user.name},
                "result_type": participant.result_type,
                "progress": float(participant.progress or 0),
                "place": participant.place,
                "attempts_count": len(student_submissions),
                "latest_submission": _sub_out(latest_submission),
                "final_submission": _sub_out(final_submission),
            }
        )
    return logs


def list_battle_rooms_log(battle_id):
    battle_uuid = as_uuid(battle_id)
    room_rows = (
        db.session.query(Room)
        .filter(Room.battle_id == battle_uuid)
        .order_by(Room.created_at.desc())
        .all()
    )
    if not room_rows:
        return []

    room_ids = [room.id for room in room_rows]
    match_rows = (
        db.session.query(Match, Task)
        .join(Task, Task.id == Match.task_id)
        .filter(Match.room_id.in_(room_ids))
        .order_by(Match.created_at.desc())
        .all()
    )
    match_by_room = {}
    for match, task in match_rows:
        match_by_room.setdefault(match.room_id, []).append((match, task))

    match_ids = [match.id for match, _ in match_rows]
    participants_rows = []
    if match_ids:
        participants_rows = (
            db.session.query(MatchParticipant, User)
            .join(User, User.id == MatchParticipant.student_id)
            .filter(MatchParticipant.match_id.in_(match_ids))
            .all()
        )
    participants_by_match = {}
    for p, u in participants_rows:
        participants_by_match.setdefault(p.match_id, []).append((p, u))

    result = []
    for room in room_rows:
        room_matches = match_by_room.get(room.id, [])
        latest_match, latest_task = room_matches[0] if room_matches else (None, None)
        latest_participants = participants_by_match.get(latest_match.id, []) if latest_match else []
        latest_participants.sort(key=lambda item: item[1].name.lower())

        result.append(
            {
                "room_id": str(room.id),
                "status": room.status,
                "created_at": room.created_at.isoformat() if room.created_at else None,
                "finished_at": room.finished_at.isoformat() if room.finished_at else None,
                "latest_match": {
                    "match_id": str(latest_match.id),
                    "task": {
                        "id": str(latest_task.id),
                        "title": latest_task.title,
                        "difficulty": latest_task.difficulty,
                        "statement_md": latest_task.statement_md,
                    },
                    "participants": [
                        {
                            "student": {"id": str(u.id), "name": u.name},
                            "result_type": p.result_type,
                            "progress": float(p.progress or 0),
                            "place": p.place,
                            "is_disconnected": bool(p.is_disconnected),
                            "is_online": not bool(p.is_disconnected),
                        }
                        for p, u in latest_participants
                    ],
                }
                if latest_match
                else None,
                "matches_count": len(room_matches),
            }
        )

    return result


def get_battle_room_log_or_none(battle_id, room_id):
    room = (
        db.session.query(Room)
        .filter(Room.id == as_uuid(room_id), Room.battle_id == as_uuid(battle_id))
        .first()
    )
    if not room:
        return None

    matches_rows = (
        db.session.query(Match, Task)
        .join(Task, Task.id == Match.task_id)
        .filter(Match.room_id == room.id)
        .order_by(Match.created_at.asc())
        .all()
    )
    matches = [m for m, _ in matches_rows]
    match_ids = [m.id for m in matches]
    task_by_match = {m.id: t for m, t in matches_rows}

    participants_rows = []
    submissions_rows = []
    if match_ids:
        participants_rows = (
            db.session.query(MatchParticipant, User)
            .join(User, User.id == MatchParticipant.student_id)
            .filter(MatchParticipant.match_id.in_(match_ids))
            .all()
        )
        submissions_rows = (
            db.session.query(Submission, User)
            .join(User, User.id == Submission.student_id)
            .filter(Submission.match_id.in_(match_ids))
            .order_by(Submission.created_at.asc())
            .all()
        )

    participants_by_match = {}
    for p, u in participants_rows:
        participants_by_match.setdefault(p.match_id, []).append((p, u))
    for mid in participants_by_match:
        participants_by_match[mid].sort(key=lambda item: item[1].name.lower())

    submissions_by_match = {}
    for s, u in submissions_rows:
        submissions_by_match.setdefault(s.match_id, []).append((s, u))

    matches_out = []
    for match in matches:
        task = task_by_match.get(match.id)
        match_participants = participants_by_match.get(match.id, [])
        match_submissions = submissions_by_match.get(match.id, [])
        matches_out.append(
            {
                "match_id": str(match.id),
                "created_at": match.created_at.isoformat() if match.created_at else None,
                "finished_at": match.finished_at.isoformat() if match.finished_at else None,
                "finished_by": match.finished_by,
                "task": {
                    "id": str(task.id),
                    "title": task.title,
                    "difficulty": task.difficulty,
                    "statement_md": task.statement_md,
                }
                if task
                else None,
                "participants": [
                    {
                        "student": {"id": str(u.id), "name": u.name},
                        "result_type": p.result_type,
                        "progress": float(p.progress or 0),
                        "place": p.place,
                        "accepted_at": p.accepted_at.isoformat() if p.accepted_at else None,
                        "is_disconnected": bool(p.is_disconnected),
                        "is_online": not bool(p.is_disconnected),
                    }
                    for p, u in match_participants
                ],
                "submissions": [
                    {
                        "submission_id": str(s.id),
                        "student": {"id": str(u.id), "name": u.name},
                        "language": s.language,
                        "verdict": s.verdict,
                        "progress": float(s.progress_value or 0),
                        "visible_tests_passed": s.visible_tests_passed,
                        "visible_tests_total": s.visible_tests_total,
                        "hidden_tests_passed": s.hidden_tests_passed,
                        "hidden_tests_total": s.hidden_tests_total,
                        "created_at": s.created_at.isoformat() if s.created_at else None,
                        "source_code": s.source_code,
                    }
                    for s, u in match_submissions
                ],
            }
        )

    return {
        "room": {
            "room_id": str(room.id),
            "status": room.status,
            "created_at": room.created_at.isoformat() if room.created_at else None,
            "finished_at": room.finished_at.isoformat() if room.finished_at else None,
        },
        "matches": matches_out,
    }


def get_battle_submission_or_none(battle_id, submission_id):
    row = (
        db.session.query(Submission, Match, Room, User, Task)
        .join(Match, Match.id == Submission.match_id)
        .join(Room, Room.id == Match.room_id)
        .join(User, User.id == Submission.student_id)
        .join(Task, Task.id == Match.task_id)
        .filter(Submission.id == as_uuid(submission_id), Room.battle_id == as_uuid(battle_id))
        .first()
    )
    if not row:
        return None
    submission, match, room, user, task = row
    return {
        "id": str(submission.id),
        "room_id": str(room.id),
        "match_id": str(match.id),
        "task": {"id": str(task.id), "title": task.title, "difficulty": task.difficulty},
        "student": {"id": str(user.id), "name": user.name},
        "language": submission.language,
        "verdict": submission.verdict,
        "created_at": submission.created_at.isoformat() if submission.created_at else None,
        "visible_tests_passed": submission.visible_tests_passed,
        "visible_tests_total": submission.visible_tests_total,
        "source_code": submission.source_code,
    }


def recheck_battle_submission(*, battle_id, submission_id, callback_url):
    row = (
        db.session.query(Submission, Match, Room, Task)
        .join(Match, Match.id == Submission.match_id)
        .join(Room, Room.id == Match.room_id)
        .join(Task, Task.id == Match.task_id)
        .filter(Submission.id == as_uuid(submission_id), Room.battle_id == as_uuid(battle_id))
        .first()
    )
    if not row:
        return None, "submission_not_found"

    original_submission, match, room, task = row
    cloned = rooms_service.create_submission(
        match_id=original_submission.match_id,
        student_id=original_submission.student_id,
        language=original_submission.language,
        source_code=original_submission.source_code,
    )
    realtime_service.emit_submission_queued(match.id, cloned.student_id, battle_id=room.battle_id)

    try:
        external = rooms_service.submit_to_checker(
            submission=cloned,
            callback_url=callback_url,
            task_text=(task.statement_md if task else ""),
            check_type=(task.check_type if task else "tests"),
            check_config=(task.config_json if task else {}),
        )
    except Exception as exc:
        rooms_service.mark_submission_checker_error(cloned, exc)
        realtime_service.emit_submission_verdict(
            match.id,
            cloned.student_id,
            "internal_error",
            0,
            battle_id=room.battle_id,
            visible_tests_passed=0,
            visible_tests_total=None,
        )
        return cloned, "checker_submit_failed"

    return {"submission": cloned, "external": external}, None
