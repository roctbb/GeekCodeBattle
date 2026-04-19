import time
from functools import wraps
import uuid

import jwt
from flask import current_app, jsonify, request, session

from .extensions import db
from .models import User


def _decode_geekclass_jwt(token: str) -> dict:
    payload = jwt.decode(token, current_app.config["JWT_SECRET"], algorithms=["HS256"])
    iat = payload.get("iat", 0)
    if time.time() - iat > 60:
        raise ValueError("JWT token expired")
    return payload


def process_login_token(token: str) -> User:
    payload = _decode_geekclass_jwt(token)
    external_id = str(payload["id"])
    user = User.query.filter_by(external_id=external_id).first()
    if user is None:
        user = User(external_id=external_id, name=payload.get("name", "Unknown"), role=payload.get("role", "student"))
        db.session.add(user)
    else:
        user.name = payload.get("name", user.name)
        user.role = payload.get("role", user.role)
    db.session.commit()

    session["user_id"] = str(user.id)
    session["role"] = user.role
    return user


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    try:
        return db.session.get(User, uuid.UUID(str(user_id)))
    except Exception:
        return None


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Unauthorized"}), 401
        return fn(*args, **kwargs)

    return wrapper


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                return jsonify({"error": "Unauthorized"}), 401
            if session.get("role") not in roles:
                return jsonify({"error": "Forbidden"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator
