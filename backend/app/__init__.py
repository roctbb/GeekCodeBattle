from flask import Flask, jsonify
from flask_cors import CORS
from flask import session, request
from flask_socketio import join_room, leave_room

from .config import Config
from .celery_app import init_celery
from .extensions import db, migrate, socketio
from .services import presence_service, presence_runtime, realtime_service, battles_service


_socket_user_by_sid = {}
_socket_count_by_user = {}
_socket_scope_by_sid = {}


def _normalize_scope_value(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _update_socket_scopes_for_sid(sid, *, battle_id=None, room_id=None, match_id=None):
    if not sid:
        return

    next_scope = {
        "battle": _normalize_scope_value(battle_id),
        "room": _normalize_scope_value(room_id),
        "match": _normalize_scope_value(match_id),
    }
    prev_scope = _socket_scope_by_sid.get(sid, {})

    for scope_name in ("battle", "room", "match"):
        prev_id = prev_scope.get(scope_name)
        next_id = next_scope.get(scope_name)
        if prev_id and prev_id != next_id:
            leave_room(f"{scope_name}:{prev_id}")
        if next_id:
            join_room(f"{scope_name}:{next_id}")

    _socket_scope_by_sid[sid] = next_scope


def _mark_user_online(user_id):
    state = presence_service.set_user_online(user_id)
    if state.get("changed"):
        realtime_service.emit_presence_updated(
            battle_ids=state.get("battle_ids"),
            room_ids=state.get("room_ids"),
            match_ids=state.get("match_ids"),
        )
    return state


def _mark_user_offline(user_id):
    state = presence_service.set_user_offline(user_id)
    if state.get("changed"):
        realtime_service.emit_presence_updated(
            battle_ids=state.get("battle_ids"),
            room_ids=state.get("room_ids"),
            match_ids=state.get("match_ids"),
        )
    return state


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, supports_credentials=True)

    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)
    init_celery(app)
    from . import models  # noqa: F401

    from .routes.auth import auth_bp
    from .routes.battles import battles_bp
    from .routes.tasks import tasks_bp
    from .routes.queue import queue_bp
    from .routes.rooms import rooms_bp
    from .routes.matches import matches_bp
    from .routes.integrations import integrations_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(battles_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(queue_bp)
    app.register_blueprint(rooms_bp)
    app.register_blueprint(matches_bp)
    app.register_blueprint(integrations_bp)

    def _delayed_tick_battles(battle_ids):
        delay_seconds = int(app.config.get("DISCONNECT_GRACE_SECONDS", 300)) + 1
        socketio.sleep(delay_seconds)
        with app.app_context():
            for battle_id in battle_ids or []:
                battle = battles_service.get_battle_or_none(battle_id)
                if not battle:
                    continue
                battles_service.tick_timeouts(battle)

    def _enqueue_delayed_tick_battles(battle_ids):
        if not battle_ids:
            return
        if app.config.get("CELERY_ENABLED", True):
            from .celery_tasks import delayed_tick_battles_task

            delay_seconds = int(app.config.get("DISCONNECT_GRACE_SECONDS", 300)) + 1
            delayed_tick_battles_task.apply_async(args=[battle_ids], countdown=delay_seconds)
            return
        socketio.start_background_task(_delayed_tick_battles, battle_ids)

    @socketio.on("subscribe")
    def handle_subscribe(data):
        if not isinstance(data, dict):
            return
        sid = request.sid
        battle_id = data.get("battle_id")
        room_id = data.get("room_id")
        match_id = data.get("match_id")
        _update_socket_scopes_for_sid(
            sid,
            battle_id=battle_id,
            room_id=room_id,
            match_id=match_id,
        )
        user_id = session.get("user_id")
        if user_id:
            join_room(f"user:{user_id}")
            if sid and sid not in _socket_user_by_sid:
                _socket_user_by_sid[sid] = str(user_id)
                _socket_count_by_user[str(user_id)] = _socket_count_by_user.get(str(user_id), 0) + 1
                if _socket_count_by_user[str(user_id)] == 1:
                    presence_runtime.set_online(str(user_id))
                    _mark_user_online(user_id)

    @socketio.on("connect")
    def handle_connect():
        user_id = session.get("user_id")
        sid = request.sid
        if not user_id or not sid:
            return
        if sid in _socket_user_by_sid:
            return
        user_key = str(user_id)
        _socket_user_by_sid[sid] = user_key
        _socket_count_by_user[user_key] = _socket_count_by_user.get(user_key, 0) + 1
        if _socket_count_by_user[user_key] == 1:
            presence_runtime.set_online(user_key)
            _mark_user_online(user_id)

    @socketio.on("disconnect")
    def handle_disconnect():
        sid = request.sid
        _socket_scope_by_sid.pop(sid, None)
        user_key = _socket_user_by_sid.pop(sid, None)
        if not user_key:
            return
        current = _socket_count_by_user.get(user_key, 0)
        next_count = max(0, current - 1)
        if next_count == 0:
            _socket_count_by_user.pop(user_key, None)
            presence_runtime.set_offline(user_key)
            state = _mark_user_offline(user_key)
            battle_ids = state.get("battle_ids") if state else []
            if battle_ids:
                _enqueue_delayed_tick_battles(battle_ids)
        else:
            _socket_count_by_user[user_key] = next_count

    @app.get("/api/v1/health")
    def health():
        return jsonify({"status": "ok"})

    if app.config.get("AUTO_CREATE_DB", False):
        with app.app_context():
            try:
                db.create_all()
            except Exception:
                # Database may be unavailable during local import checks.
                pass

    return app
