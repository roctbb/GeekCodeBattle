from __future__ import annotations

import random
from datetime import datetime, timezone
from flask import current_app

from ..extensions import db
from ..models import (
    Battle,
    QueueEntry,
    Room,
    Match,
    MatchParticipant,
    BattleTask,
    Task,
    User,
)

DIFFICULTY_RANK = {"easy": 0, "medium": 1, "hard": 2}


def _target_difficulty_for_rating(avg_rating: float) -> str:
    if avg_rating >= 1450:
        return "hard"
    if avg_rating >= 1100:
        return "medium"
    return "easy"


def _difficulty_preference(target: str) -> list[str]:
    if target == "hard":
        return ["hard", "medium", "easy"]
    if target == "medium":
        return ["medium", "hard", "easy"]
    return ["easy", "medium", "hard"]


def _build_rating_map(user_ids: list) -> dict:
    if not user_ids:
        return {}
    rows = db.session.query(User.id, User.rating).filter(User.id.in_(user_ids)).all()
    return {uid: int(rating or 1000) for uid, rating in rows}


def _find_active_participant_ids(battle_id, user_ids: list) -> set:
    if not user_ids:
        return set()
    rows = (
        db.session.query(MatchParticipant.student_id)
        .join(Match, Match.id == MatchParticipant.match_id)
        .join(Room, Room.id == Match.room_id)
        .filter(
            Room.battle_id == battle_id,
            Match.finished_at.is_(None),
            MatchParticipant.student_id.in_(user_ids),
        )
        .distinct()
        .all()
    )
    return {student_id for (student_id,) in rows}


def _choose_task_for_group(battle_id, user_ids: list, rating_map: dict | None = None) -> Task | None:
    task_ids = [row.task_id for row in BattleTask.query.filter_by(battle_id=battle_id).all()]
    if not task_ids:
        task_ids = [row.id for row in Task.query.filter_by(is_active=True).all()]
    if not task_ids:
        return None

    # Exclude tasks that any participant already received in this battle.
    used_task_ids = set()
    if user_ids:
        rows = (
            db.session.query(Match.task_id)
            .join(Room, Room.id == Match.room_id)
            .join(MatchParticipant, MatchParticipant.match_id == Match.id)
            .filter(Room.battle_id == battle_id, MatchParticipant.student_id.in_(user_ids))
            .all()
        )
        used_task_ids = {row[0] for row in rows}

    candidate_ids = [tid for tid in task_ids if tid not in used_task_ids]
    if not candidate_ids:
        candidate_ids = task_ids

    candidate_tasks = (
        db.session.query(Task)
        .filter(Task.id.in_(candidate_ids))
        .all()
    )
    if not candidate_tasks:
        return None

    rating_map = rating_map or {}
    avg_rating = (
        sum(int(rating_map.get(uid, 1000)) for uid in user_ids) / len(user_ids)
        if user_ids
        else 1000
    )
    target = _target_difficulty_for_rating(avg_rating)

    by_difficulty = {"easy": [], "medium": [], "hard": []}
    for task in candidate_tasks:
        diff = str(task.difficulty or "").lower()
        if diff in by_difficulty:
            by_difficulty[diff].append(task)

    for diff in _difficulty_preference(target):
        options = by_difficulty.get(diff) or []
        if options:
            random.shuffle(options)
            return options[0]

    # Unknown difficulty fallback.
    random.shuffle(candidate_tasks)
    return candidate_tasks[0]


def _normalize_room_size(room_size) -> int:
    try:
        size = int(room_size)
    except (TypeError, ValueError):
        size = 2
    return max(2, size)


def _split_ready_entries_by_rating(ready_entries: list[QueueEntry], rating_map: dict, room_size: int) -> list[list[QueueEntry]]:
    if len(ready_entries) < 2:
        return []
    room_size = _normalize_room_size(room_size)

    sorted_entries = sorted(
        ready_entries,
        key=lambda entry: int(rating_map.get(entry.user_id, 1000)),
        reverse=True,
    )

    if room_size == 2:
        if len(sorted_entries) == 3:
            return [sorted_entries]

        groups = []
        idx = 0
        while idx + 1 < len(sorted_entries):
            groups.append([sorted_entries[idx], sorted_entries[idx + 1]])
            idx += 2

        # Odd player: merge into the last group.
        if idx < len(sorted_entries):
            if groups:
                groups[-1].append(sorted_entries[idx])
            else:
                groups.append([sorted_entries[idx]])
        return [g for g in groups if len(g) >= 2]

    if len(sorted_entries) < room_size:
        return []

    groups = []
    idx = 0
    while idx + room_size <= len(sorted_entries):
        groups.append(sorted_entries[idx:idx + room_size])
        idx += room_size

    return groups


def _remember_opponents(user_ids: list):
    for uid in user_ids:
        user = db.session.get(User, uid)
        if not user:
            continue
        others = [str(x) for x in user_ids if x != uid]
        current = list(user.last_opponents_json or [])
        merged = (others + current)[:20]
        user.last_opponents_json = merged


def _create_room_and_match(battle: Battle, group: list[QueueEntry]):
    user_ids = [entry.user_id for entry in group]
    if _find_active_participant_ids(battle.id, user_ids):
        return None

    room = Room(battle_id=battle.id, status="active", started_at=datetime.now(timezone.utc))
    db.session.add(room)
    db.session.flush()

    rating_map = _build_rating_map(user_ids)
    task = _choose_task_for_group(battle.id, user_ids, rating_map=rating_map)
    if task is None:
        room.status = "cancelled"
        return None

    match = Match(room_id=room.id, task_id=task.id)
    db.session.add(match)
    db.session.flush()

    for entry in group:
        db.session.add(MatchParticipant(match_id=match.id, student_id=entry.user_id, progress=0))
        db.session.delete(entry)

    _remember_opponents(user_ids)

    return {"room_id": str(room.id), "match_id": str(match.id), "task_id": str(task.id), "participant_ids": [str(u) for u in user_ids]}


def run_matchmaking(battle_id) -> list[dict]:
    battle = db.session.get(Battle, battle_id)
    if not battle or battle.status != "running":
        return []

    created = []
    delay_seconds = int(current_app.config.get("MATCHMAKING_DELAY_SECONDS", 10))

    ready_entries = (
        QueueEntry.query
        .filter_by(battle_id=battle.id, is_ready=True)
        .order_by(QueueEntry.enqueued_at.asc())
        .with_for_update()
        .all()
    )
    if ready_entries:
        active_ids = _find_active_participant_ids(battle.id, [entry.user_id for entry in ready_entries])
        ready_entries = [entry for entry in ready_entries if entry.user_id not in active_ids]

    if len(ready_entries) >= 2:
        rating_map = _build_rating_map([entry.user_id for entry in ready_entries])
        groups = _split_ready_entries_by_rating(ready_entries, rating_map, battle.room_size)
        if not groups:
            db.session.commit()
            return created

        oldest_enqueued = min(entry.enqueued_at for group in groups for entry in group)
        if oldest_enqueued.tzinfo is None:
            oldest_enqueued = oldest_enqueued.replace(tzinfo=timezone.utc)
        oldest_wait = (datetime.now(timezone.utc) - oldest_enqueued).total_seconds()

        if oldest_wait >= delay_seconds:
            for group in groups:
                created_room = _create_room_and_match(battle, group)
                if created_room:
                    created.append(created_room)

    db.session.commit()
    return created


def run_matchmaking_for_battle_id(battle_id_str: str):
    from ..utils import as_uuid

    return run_matchmaking(as_uuid(battle_id_str))
