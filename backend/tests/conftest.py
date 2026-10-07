import os
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def app(tmp_path, monkeypatch):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app import create_app
    from app.extensions import db
    from app.services import rooms_service, integrations_service
    app = create_app({
        'TESTING': True, 'DEBUG': False, 'SECRET_KEY': 'test-only', 'JWT_SECRET': 'test-only',
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{tmp_path / "test.db"}',
        'AUTO_CREATE_DB': True, 'GEEKPASTE_CALLBACK_REQUIRE_AUTH': False,
        'MATCHMAKING_DELAY_SECONDS': 1, 'CELERY_ENABLED': False,
        'ROUND_TIMEOUT_BACKGROUND_ENABLED': False, 'ENABLE_DEV_LOGIN': True,
        'SOCKETIO_MESSAGE_QUEUE': '', 'SESSION_COOKIE_SECURE': False,
        'PROXY_FIX_ENABLED': False, 'BACKEND_URL': 'http://localhost:8090',
    })
    monkeypatch.setattr(rooms_service, 'submit_for_check', lambda **kw: {'job_id': kw['callback_id']})
    monkeypatch.setattr(integrations_service, 'callback_is_duplicate', lambda *args: False)
    monkeypatch.setattr(integrations_service, 'mark_callback_processed', lambda *args: None)
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture()
def client(app):
    return app.test_client()
