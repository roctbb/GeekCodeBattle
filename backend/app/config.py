import os
from pathlib import Path
from dotenv import load_dotenv

# Single source of truth: project-root .env
ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ROOT_ENV)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    _pg_user = os.getenv("POSTGRES_USER", "geekcodebattle")
    _pg_password = os.getenv("POSTGRES_PASSWORD", "geekcodebattle")
    _pg_db = os.getenv("POSTGRES_DB", "geekcodebattle")
    _pg_host = os.getenv("POSTGRES_HOST", "localhost")
    _pg_port = os.getenv("POSTGRES_PORT", "5432")

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    DEBUG = env_bool("DEBUG", False)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "CONNECTION_STRING",
        f"postgresql+psycopg2://{_pg_user}:{_pg_password}@{_pg_host}:{_pg_port}/{_pg_db}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
    GEEKCLASS_HOST = os.getenv("GEEKCLASS_HOST", "https://codingprojects.ru")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8086")
    ENABLE_GEEKCLASS_LOGIN = env_bool("ENABLE_GEEKCLASS_LOGIN", True)
    ENABLE_DEV_LOGIN = env_bool("ENABLE_DEV_LOGIN", False)

    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
    GEEKPASTE_API_URL = os.getenv("GEEKPASTE_API_URL", "http://paste:8084/api/external/check")
    GEEKPASTE_CALLBACK_REQUIRE_AUTH = env_bool("GEEKPASTE_CALLBACK_REQUIRE_AUTH", True)
    GEEKPASTE_CALLBACK_EXPECTED_SERVICE = os.getenv("GEEKPASTE_CALLBACK_EXPECTED_SERVICE", "geekpaste")
    GEEKPASTE_CALLBACK_MAX_AGE_SECONDS = int(os.getenv("GEEKPASTE_CALLBACK_MAX_AGE_SECONDS", "120"))
    GEEKPASTE_CALLBACK_DEDUP_TTL_SECONDS = int(os.getenv("GEEKPASTE_CALLBACK_DEDUP_TTL_SECONDS", "86400"))

    ROUND_DURATION_MINUTES = int(os.getenv("ROUND_DURATION_MINUTES", "20"))
    POST_WIN_GRACE_MINUTES = int(os.getenv("POST_WIN_GRACE_MINUTES", "5"))
    DISCONNECT_GRACE_SECONDS = int(os.getenv("DISCONNECT_GRACE_SECONDS", "300"))
    MATCHMAKING_DELAY_SECONDS = int(os.getenv("MATCHMAKING_DELAY_SECONDS", "10"))
    ROUND_TIMEOUT_BACKGROUND_ENABLED = env_bool("ROUND_TIMEOUT_BACKGROUND_ENABLED", True)
    ROUND_TIMEOUT_POLL_SECONDS = int(os.getenv("ROUND_TIMEOUT_POLL_SECONDS", "2"))
    AUTO_CREATE_DB = env_bool("AUTO_CREATE_DB", False)

    JSON_AS_ASCII = False
