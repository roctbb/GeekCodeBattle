from urllib.parse import quote, urlparse

from flask import Blueprint, request, session, current_app, redirect

from ..api.responses import ok, fail
from ..api.serializers import user_out
from ..auth import process_login_token, current_user, login_required
from ..extensions import db
from ..models import User


auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1")


def _sanitize_next_url(next_url: str | None) -> str:
    raw = (next_url or "").strip()
    if not raw:
        return "/"

    frontend_base = str(current_app.config.get("FRONTEND_URL", "http://localhost:5173")).rstrip("/")
    frontend_netloc = urlparse(frontend_base).netloc
    parsed = urlparse(raw)
    if parsed.scheme or parsed.netloc:
        if parsed.netloc and parsed.netloc != frontend_netloc:
            return "/"
        path = parsed.path or "/"
        if not path.startswith("/"):
            path = "/" + path
        if parsed.query:
            path = f"{path}?{parsed.query}"
        if parsed.fragment:
            path = f"{path}#{parsed.fragment}"
        return path

    if not raw.startswith("/"):
        return "/"
    return raw


def _frontend_redirect(next_path: str):
    frontend_base = str(current_app.config.get("FRONTEND_URL", "http://localhost:5173")).rstrip("/")
    target = next_path or "/"
    if target == "/":
        return redirect(frontend_base)
    return redirect(frontend_base + target)


@auth_bp.get("/auth/options")
def auth_options():
    return ok(
        {
            "dev_login_enabled": bool(current_app.config.get("ENABLE_DEV_LOGIN", False)),
            "geekclass_enabled": bool(current_app.config.get("ENABLE_GEEKCLASS_LOGIN", True)),
        }
    )


@auth_bp.post("/auth/login/geekclass")
def login_geekclass():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else request.args.get("token")
    if not token:
        return fail("Missing token", 400)

    try:
        user = process_login_token(token)
    except Exception as exc:
        return fail(f"Invalid token: {exc}", 403)

    return ok(user_out(user))


@auth_bp.get("/auth/login")
def login_redirect():
    if not bool(current_app.config.get("ENABLE_GEEKCLASS_LOGIN", True)):
        return fail("GeekClass login is disabled", 404)
    next_url = _sanitize_next_url(request.args.get("next"))
    backend_base = str(current_app.config.get("BACKEND_URL", request.host_url.rstrip("/"))).rstrip("/")
    callback_url = backend_base + "/api/v1/auth/callback?next=" + quote(next_url, safe="")
    geekclass_host = str(current_app.config.get("GEEKCLASS_HOST", "https://codingprojects.ru")).rstrip("/")
    jwt_url = geekclass_host + "/insider/jwt?redirect_url=" + quote(callback_url, safe="")
    return redirect(jwt_url)


@auth_bp.get("/auth/callback")
def login_callback():
    token = request.args.get("token")
    next_url = _sanitize_next_url(request.args.get("next"))
    if not token:
        return _frontend_redirect(next_url)
    try:
        process_login_token(token)
    except Exception:
        return _frontend_redirect(next_url)
    return _frontend_redirect(next_url)


@auth_bp.post("/auth/logout")
def logout():
    session.clear()
    return ok()


@auth_bp.get("/me")
@login_required
def me():
    user = current_user()
    if user is None:
        return fail("Unauthorized", 401)
    return ok(user_out(user))


@auth_bp.post("/auth/dev-login")
def dev_login():
    if not bool(current_app.config.get("ENABLE_DEV_LOGIN", False)):
        return fail("Dev login is disabled", 404)

    data = request.get_json() or {}
    external_id = str(data.get("external_id") or "dev-user")
    name = data.get("name") or "Developer"
    role = data.get("role") or "student"
    if role not in {"student", "teacher", "admin"}:
        return fail("Invalid role", 400)

    user = User.query.filter_by(external_id=external_id).first()
    if user is None:
        user = User(external_id=external_id, name=name, role=role)
        db.session.add(user)
    else:
        user.name = name
        user.role = role
    db.session.commit()

    session["user_id"] = str(user.id)
    session["role"] = user.role
    return ok(user_out(user))
