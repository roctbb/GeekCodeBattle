import time

import jwt


def login(client, app, extra=None, secret=None):
    payload = {"id": 42, "name": "Участник", "role": "student", "iat": int(time.time()), **(extra or {})}
    token = jwt.encode(payload, secret or app.config["JWT_SECRET"], algorithm="HS256")
    return client.post("/api/v1/auth/login/geekclass", headers={"Authorization": "Bearer " + token})


def test_signed_avatar_survives_profile_refresh_and_player_snapshot(app, client):
    avatar = "https://codingprojects.ru/media/user_avatars/42.jpg?v=123"
    response = login(client, app, {"avatar_url": avatar})
    assert response.status_code == 200
    assert response.json["avatar_url"] == avatar
    assert client.get("/api/v1/me").json["avatar_url"] == avatar
    assert client.get("/api/v1/me/state").json["me"]["avatar_url"] == avatar


def test_legacy_login_and_dev_login_clear_previous_avatar(app, client):
    login(client, app, {"avatar_url": "https://codingprojects.ru/avatar.jpg"})
    assert login(client, app).json["avatar_url"] is None
    login(client, app, {"avatar_url": "https://codingprojects.ru/avatar.jpg"})
    response = client.post("/api/v1/auth/dev-login", json={"external_id": "another-user"})
    assert response.json["avatar_url"] is None


def test_invalid_signature_cannot_replace_avatar(app, client):
    avatar = "https://codingprojects.ru/avatar.jpg"
    login(client, app, {"avatar_url": avatar})
    assert login(client, app, {"avatar_url": "https://example.com/fake.jpg"}, secret="wrong-key").status_code == 403
    assert client.get("/api/v1/me").json["avatar_url"] == avatar
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/me").status_code == 401
