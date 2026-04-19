import os
import sys
import tempfile

import pytest


@pytest.fixture()
def app():
    db_fd, db_path = tempfile.mkstemp(prefix='gcb_test_', suffix='.db')
    os.close(db_fd)

    os.environ['CONNECTION_STRING'] = f"sqlite:///{db_path}"
    os.environ['AUTO_CREATE_DB'] = 'true'
    os.environ['GEEKPASTE_CALLBACK_REQUIRE_AUTH'] = 'false'
    os.environ['MATCHMAKING_DELAY_SECONDS'] = '1'
    os.environ['CELERY_ENABLED'] = 'false'
    os.environ['ROUND_TIMEOUT_BACKGROUND_ENABLED'] = 'false'
    os.environ['ENABLE_DEV_LOGIN'] = 'true'

    sys.path.insert(0, '/Users/roctbb/PycharmProjects/GeekCodeBattle/backend')
    from app import create_app

    app = create_app()
    yield app

    try:
        os.remove(db_path)
    except FileNotFoundError:
        pass


@pytest.fixture()
def client(app):
    return app.test_client()
