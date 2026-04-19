from flask import Blueprint, request, session

from ..api.responses import ok, fail
from ..api.serializers import task_out, task_package_out
from ..api.validators import VALID_CHECK_TYPES, VALID_DIFFICULTIES
from ..auth import login_required, role_required
from ..services import tasks_service


tasks_bp = Blueprint("tasks", __name__, url_prefix="/api/v1")


@tasks_bp.get("/tasks")
@login_required
def list_tasks():
    return ok([task_out(t) for t in tasks_service.list_tasks()])


@tasks_bp.post("/tasks")
@role_required("teacher", "admin")
def create_task():
    data = request.get_json() or {}
    for field in ("title", "statement_md", "difficulty", "check_type"):
        if not data.get(field):
            return fail(f"{field} is required", 400)

    if data["difficulty"] not in VALID_DIFFICULTIES:
        return fail("difficulty must be easy|medium|hard", 400)
    if data["check_type"] not in VALID_CHECK_TYPES:
        return fail("check_type must be tests|gpt", 400)

    task = tasks_service.create_task(
        title=data["title"],
        statement_md=data["statement_md"],
        difficulty=data["difficulty"],
        check_type=data["check_type"],
        config=data.get("config", {}),
        created_by=session["user_id"],
    )
    return ok(task_out(task), 201)


@tasks_bp.get("/tasks/<task_id>")
@login_required
def get_task(task_id):
    task = tasks_service.get_task_or_none(task_id)
    if not task:
        return fail("Not found", 404)
    return ok(task_out(task))


@tasks_bp.patch("/tasks/<task_id>")
@role_required("teacher", "admin")
def update_task(task_id):
    task = tasks_service.get_task_or_none(task_id)
    if not task:
        return fail("Not found", 404)

    data = request.get_json() or {}
    if "difficulty" in data and data["difficulty"] not in VALID_DIFFICULTIES:
        return fail("difficulty must be easy|medium|hard", 400)
    if "check_type" in data and data["check_type"] not in VALID_CHECK_TYPES:
        return fail("check_type must be tests|gpt", 400)

    return ok(task_out(tasks_service.update_task(task, data)))


@tasks_bp.delete("/tasks/<task_id>")
@role_required("teacher", "admin")
def delete_task(task_id):
    task = tasks_service.get_task_or_none(task_id)
    if not task:
        return fail("Not found", 404)
    tasks_service.delete_task(task)
    return ok({"status": "deleted"})


@tasks_bp.post("/tasks/import")
@role_required("teacher", "admin")
def import_tasks():
    payload = request.get_json()
    package_meta = None
    rows = None

    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        tasks = payload.get("tasks")
        if not isinstance(tasks, list):
            return fail("For package import, field `tasks` must be JSON array", 400)
        rows = tasks
        package_meta = {
            "name": payload.get("name"),
            "version": payload.get("version"),
            "description": payload.get("description"),
        }
    else:
        return fail("Body must be JSON array or package object with `tasks`", 400)

    created, errors = tasks_service.bulk_import_tasks(rows, session["user_id"], package_meta=package_meta)
    return ok({"created_ids": created, "errors": errors, "package": package_meta})


@tasks_bp.get("/tasks/export")
@role_required("teacher", "admin")
def export_tasks():
    tasks = tasks_service.list_tasks()
    return ok(
        {
            "format": "task-package-v1",
            "name": "exported-package",
            "version": "1.0.0",
            "tasks": [
                {
                    "title": t.title,
                    "statement_md": t.statement_md,
                    "difficulty": t.difficulty,
                    "check_type": t.check_type,
                    "languages": ["python", "cpp"],
                    "config": t.config_json,
                }
                for t in tasks
            ],
        }
    )


@tasks_bp.get("/task-packages")
@login_required
def list_task_packages():
    packages = tasks_service.list_task_packages()
    package_tasks = []
    for package in packages:
        task_count = len(tasks_service.list_tasks_in_package(package.id))
        package_tasks.append(task_package_out(package, task_count=task_count))
    return ok(package_tasks)


@tasks_bp.post("/task-packages")
@role_required("teacher", "admin")
def create_task_package():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return fail("name is required", 400)

    package = tasks_service.create_task_package(
        name=name,
        description=data.get("description"),
        created_by=session["user_id"],
    )

    rows = data.get("tasks")
    created = []
    errors = []
    if isinstance(rows, list) and rows:
        package_meta = {"name": package.name, "description": package.description}
        created, errors = tasks_service.bulk_import_tasks(
            rows,
            created_by=session["user_id"],
            package_meta=package_meta,
            package_id=package.id,
        )

    return ok(
        {
            "package": task_package_out(package, task_count=len(tasks_service.list_tasks_in_package(package.id))),
            "created_ids": created,
            "errors": errors,
        },
        201,
    )


@tasks_bp.post("/task-packages/import")
@role_required("teacher", "admin")
def import_task_package():
    payload = request.get_json() or {}
    if not isinstance(payload, dict):
        return fail("Body must be JSON object", 400)
    if "tasks" in payload and not isinstance(payload.get("tasks"), list):
        return fail("field `tasks` must be array", 400)

    package, created, errors = tasks_service.import_package(payload, session["user_id"])
    return ok(
        {
            "package": task_package_out(package, task_count=len(tasks_service.list_tasks_in_package(package.id))),
            "created_ids": created,
            "errors": errors,
        },
        201,
    )


@tasks_bp.get("/task-packages/<package_id>")
@login_required
def get_task_package(package_id):
    package = tasks_service.get_task_package_or_none(package_id)
    if not package:
        return fail("Not found", 404)
    tasks = tasks_service.list_tasks_in_package(package.id)
    return ok(
        {
            "package": task_package_out(package, task_count=len(tasks)),
            "tasks": [task_out(t) for t in tasks],
        }
    )


@tasks_bp.patch("/task-packages/<package_id>")
@role_required("teacher", "admin")
def update_task_package(package_id):
    package = tasks_service.get_task_package_or_none(package_id)
    if not package:
        return fail("Not found", 404)
    data = request.get_json() or {}
    if "name" in data and not (data.get("name") or "").strip():
        return fail("name cannot be empty", 400)
    if "name" in data:
        data["name"] = data["name"].strip()
    updated = tasks_service.update_task_package(package, data)
    return ok(task_package_out(updated, task_count=len(tasks_service.list_tasks_in_package(updated.id))))


@tasks_bp.delete("/task-packages/<package_id>")
@role_required("teacher", "admin")
def delete_task_package(package_id):
    package = tasks_service.get_task_package_or_none(package_id)
    if not package:
        return fail("Not found", 404)
    tasks_service.delete_task_package(package)
    return ok({"status": "deleted"})


@tasks_bp.get("/task-packages/<package_id>/export")
@role_required("teacher", "admin")
def export_task_package(package_id):
    package = tasks_service.get_task_package_or_none(package_id)
    if not package:
        return fail("Not found", 404)
    tasks = tasks_service.list_tasks_in_package(package.id)
    return ok(
        {
            "format": "task-package-v1",
            "name": package.name,
            "description": package.description,
            "version": "1.0.0",
            "tasks": [
                {
                    "title": t.title,
                    "statement_md": t.statement_md,
                    "difficulty": t.difficulty,
                    "check_type": t.check_type,
                    "languages": ["python", "cpp"],
                    "config": t.config_json,
                }
                for t in tasks
            ],
        }
    )


@tasks_bp.post("/task-packages/<package_id>/tasks")
@role_required("teacher", "admin")
def add_task_to_package(package_id):
    package = tasks_service.get_task_package_or_none(package_id)
    if not package:
        return fail("Not found", 404)
    data = request.get_json() or {}

    task_id = data.get("task_id")
    if task_id:
        task, err = tasks_service.add_existing_task_to_package(package, task_id)
        if err == "task_not_found":
            return fail("Task not found", 404)
        return ok(task_out(task))

    for field in ("title", "statement_md", "difficulty", "check_type"):
        if not data.get(field):
            return fail(f"{field} is required", 400)
    if data["difficulty"] not in VALID_DIFFICULTIES:
        return fail("difficulty must be easy|medium|hard", 400)
    if data["check_type"] not in VALID_CHECK_TYPES:
        return fail("check_type must be tests|gpt", 400)

    task = tasks_service.create_task_in_package(
        package=package,
        title=data["title"],
        statement_md=data["statement_md"],
        difficulty=data["difficulty"],
        check_type=data["check_type"],
        config=data.get("config", {}),
        created_by=session["user_id"],
    )
    return ok(task_out(task), 201)


@tasks_bp.patch("/task-packages/<package_id>/tasks/<task_id>")
@role_required("teacher", "admin")
def update_task_in_package(package_id, task_id):
    task = tasks_service.get_task_in_package_or_none(package_id, task_id)
    if not task:
        return fail("Task not found in package", 404)
    data = request.get_json() or {}
    if "difficulty" in data and data["difficulty"] not in VALID_DIFFICULTIES:
        return fail("difficulty must be easy|medium|hard", 400)
    if "check_type" in data and data["check_type"] not in VALID_CHECK_TYPES:
        return fail("check_type must be tests|gpt", 400)
    updated = tasks_service.update_task(task, data)
    return ok(task_out(updated))


@tasks_bp.delete("/task-packages/<package_id>/tasks/<task_id>")
@role_required("teacher", "admin")
def remove_task_from_package(package_id, task_id):
    package = tasks_service.get_task_package_or_none(package_id)
    if not package:
        return fail("Not found", 404)
    removed = tasks_service.remove_task_from_package(package.id, task_id)
    return ok({"removed": removed})
