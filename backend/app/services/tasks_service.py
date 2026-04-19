from ..extensions import db
from ..models import Task, TaskPackage, TaskPackageTask, BattleTaskPackage
from ..utils import as_uuid


def list_tasks():
    return Task.query.order_by(Task.created_at.desc()).all()


def get_task_or_none(task_id):
    return db.session.get(Task, as_uuid(task_id))


def create_task(*, title, statement_md, difficulty, check_type, config, created_by):
    task = Task(
        title=title,
        statement_md=statement_md,
        difficulty=difficulty,
        check_type=check_type,
        config_json=config or {},
        created_by=as_uuid(created_by),
    )
    db.session.add(task)
    db.session.commit()
    return task


def update_task(task, data):
    if "title" in data:
        task.title = data["title"]
    if "statement_md" in data:
        task.statement_md = data["statement_md"]
    if "difficulty" in data:
        task.difficulty = data["difficulty"]
    if "check_type" in data:
        task.check_type = data["check_type"]
    if "config" in data:
        task.config_json = data["config"]
    if "is_active" in data:
        task.is_active = bool(data["is_active"])
    db.session.commit()
    return task


def delete_task(task):
    db.session.delete(task)
    db.session.commit()


def list_task_packages():
    return TaskPackage.query.order_by(TaskPackage.created_at.desc()).all()


def get_task_package_or_none(package_id):
    return db.session.get(TaskPackage, as_uuid(package_id))


def list_tasks_in_package(package_id):
    return (
        db.session.query(Task)
        .join(TaskPackageTask, TaskPackageTask.task_id == Task.id)
        .filter(TaskPackageTask.package_id == as_uuid(package_id))
        .order_by(Task.created_at.desc())
        .all()
    )


def create_task_package(*, name, description, created_by):
    package = TaskPackage(
        name=name,
        description=description,
        created_by=as_uuid(created_by),
    )
    db.session.add(package)
    db.session.commit()
    return package


def update_task_package(package, data):
    if "name" in data and data["name"] is not None:
        package.name = data["name"]
    if "description" in data:
        package.description = data["description"]
    db.session.commit()
    return package


def delete_task_package(package):
    TaskPackageTask.query.filter_by(package_id=package.id).delete()
    BattleTaskPackage.query.filter_by(package_id=package.id).delete()
    db.session.delete(package)
    db.session.commit()


def add_existing_task_to_package(package, task_id):
    task = db.session.get(Task, as_uuid(task_id))
    if not task:
        return None, "task_not_found"
    existing = TaskPackageTask.query.filter_by(package_id=package.id, task_id=task.id).first()
    if existing:
        return task, None
    db.session.add(TaskPackageTask(package_id=package.id, task_id=task.id))
    db.session.commit()
    return task, None


def create_task_in_package(*, package, title, statement_md, difficulty, check_type, config, created_by):
    task = Task(
        title=title,
        statement_md=statement_md,
        difficulty=difficulty,
        check_type=check_type,
        config_json=config or {},
        created_by=as_uuid(created_by),
    )
    db.session.add(task)
    db.session.flush()
    db.session.add(TaskPackageTask(package_id=package.id, task_id=task.id))
    db.session.commit()
    return task


def get_task_in_package_or_none(package_id, task_id):
    return (
        db.session.query(Task)
        .join(TaskPackageTask, TaskPackageTask.task_id == Task.id)
        .filter(TaskPackageTask.package_id == as_uuid(package_id), Task.id == as_uuid(task_id))
        .first()
    )


def remove_task_from_package(package_id, task_id):
    rel = TaskPackageTask.query.filter_by(package_id=as_uuid(package_id), task_id=as_uuid(task_id)).first()
    if not rel:
        return False
    db.session.delete(rel)
    db.session.commit()
    return True


def bulk_import_tasks(rows, created_by, package_meta=None, package_id=None):
    created = []
    errors = []
    for idx, row in enumerate(rows):
        try:
            for field in ("title", "statement_md", "difficulty", "check_type"):
                if not row.get(field):
                    errors.append({"index": idx, "error": f"{field} is required"})
                    raise ValueError("invalid_row")
            config = row.get("config", {})
            if not isinstance(config, dict):
                config = {}
            if package_meta:
                config = {**config, "_package": package_meta}
            task = Task(
                title=row["title"],
                statement_md=row["statement_md"],
                difficulty=row["difficulty"],
                check_type=row["check_type"],
                config_json=config,
                created_by=as_uuid(created_by),
            )
            db.session.add(task)
            db.session.flush()
            if package_id is not None:
                db.session.add(TaskPackageTask(package_id=as_uuid(package_id), task_id=task.id))
            created.append(str(task.id))
        except Exception as exc:
            if str(exc) == "invalid_row":
                continue
            errors.append({"index": idx, "error": str(exc)})
    db.session.commit()
    return created, errors


def import_package(payload, created_by):
    package_name = (payload.get("name") or "Imported package").strip()
    package_description = payload.get("description")
    package_version = payload.get("version")
    package = TaskPackage(
        name=package_name,
        description=package_description,
        created_by=as_uuid(created_by),
    )
    db.session.add(package)
    db.session.flush()

    package_meta = {
        "name": package_name,
        "version": package_version,
        "description": package_description,
    }
    rows = payload.get("tasks", []) or []
    created, errors = bulk_import_tasks(
        rows,
        created_by=created_by,
        package_meta=package_meta,
        package_id=package.id,
    )
    db.session.refresh(package)
    return package, created, errors
