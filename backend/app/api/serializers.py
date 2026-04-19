def user_out(user):
    return {
        "id": str(user.id),
        "external_id": user.external_id,
        "name": user.name,
        "role": user.role,
        "rating": user.rating,
        "season_points": user.season_points,
        "win_streak": user.win_streak,
        "loss_streak": user.loss_streak,
    }


def battle_out(battle):
    return {
        "id": str(battle.id),
        "title": battle.title,
        "status": battle.status,
        "room_size": battle.room_size,
        "started_at": battle.started_at.isoformat() if battle.started_at else None,
        "finished_at": battle.finished_at.isoformat() if battle.finished_at else None,
        "created_by": str(battle.created_by),
    }


def task_out(task):
    return {
        "id": str(task.id),
        "title": task.title,
        "statement_md": task.statement_md,
        "difficulty": task.difficulty,
        "check_type": task.check_type,
        "config": task.config_json,
        "is_active": task.is_active,
        "created_by": str(task.created_by),
    }


def task_package_out(package, task_count=None):
    return {
        "id": str(package.id),
        "name": package.name,
        "description": package.description,
        "created_by": str(package.created_by),
        "created_at": package.created_at.isoformat() if package.created_at else None,
        "updated_at": package.updated_at.isoformat() if package.updated_at else None,
        "task_count": task_count,
    }


def participant_out(p):
    return {
        "student_id": str(p.student_id),
        "result_type": p.result_type,
        "accepted_at": p.accepted_at.isoformat() if p.accepted_at else None,
        "disconnected_at": p.disconnected_at.isoformat() if p.disconnected_at else None,
        "progress": float(p.progress) if p.progress is not None else None,
        "place": p.place,
        "is_disconnected": p.is_disconnected,
        "is_online": not bool(p.is_disconnected),
    }
