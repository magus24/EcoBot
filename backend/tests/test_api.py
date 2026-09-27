"""Интеграционные тесты REST API: `pytest backend/tests`.

Тесты работают на временной SQLite-базе и временном каталоге загрузок,
поэтому не трогают данные из `backend/ecobot.db`.
"""

import io
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture()
def client(monkeypatch):
    tmp = tempfile.mkdtemp()
    monkeypatch.setenv("DATABASE_PATH", os.path.join(tmp, "test.db"))
    monkeypatch.setenv("UPLOAD_FOLDER", os.path.join(tmp, "media"))
    monkeypatch.setenv("SECRET_KEY", "test-secret")

    for name in ("config", "db", "auth", "api"):
        sys.modules.pop(name, None)

    import api
    from db import init_db

    init_db()
    with api.app.test_client() as test_client:
        yield test_client


@pytest.fixture()
def account(client):
    client.post("/users", json={"username": "admin", "email": "a@b.c", "password": "pw"})
    return client.post("/login", json={"username": "admin", "password": "pw"}).get_json()


@pytest.fixture()
def auth(account):
    return {"Authorization": f"Bearer {account['token']}"}


def upload(client, auth, address="Gota", mac="AA:BB:CC"):
    res = client.post(
        f"/add/{address}/{mac}",
        headers=auth,
        data={"file": (io.BytesIO(b"fake-jpeg"), "frame.jpg")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 201
    return res.get_json()["image"]


# ── Пользователи и вход ──────────────────────────────────────────────────────


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_first_user_can_register_then_registration_closes(client):
    res = client.post("/users", json={"username": "admin", "email": "a@b.c", "password": "pw"})
    assert res.status_code == 201

    res = client.post("/users", json={"username": "eve", "email": "e@b.c", "password": "pw"})
    assert res.status_code == 403


def test_registration_requires_all_fields(client):
    res = client.post("/users", json={"username": "admin"})
    assert res.status_code == 400


def test_login_returns_token_and_rejects_bad_password(client, auth):
    assert client.post("/login", json={"username": "admin", "password": "pw"}).status_code == 200
    assert client.post("/login", json={"username": "admin", "password": "nope"}).status_code == 401
    assert client.post("/login", json={"username": "ghost", "password": "pw"}).status_code == 401


def test_password_is_stored_hashed(client, auth):
    from db import get_db

    with get_db() as conn:
        stored = conn.execute("SELECT password_hash FROM users").fetchone()["password_hash"]

    assert "pw" not in stored
    assert stored.startswith(("scrypt:", "pbkdf2:"))


def test_legacy_login_route_still_works(client, auth):
    assert client.get("/valid/admin/pw").get_json()["status"] == "Yes"
    assert client.get("/valid/admin/wrong").status_code == 401


# ── Токены ───────────────────────────────────────────────────────────────────


def test_protected_routes_require_token(client, auth):
    for path in ("/fetch/admin", "/fetchv/admin", "/fetch_all", "/count/admin"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers=auth).status_code == 200


def test_invalid_token_is_rejected(client, auth):
    assert client.get("/fetch/admin", headers={"Authorization": "Bearer nope"}).status_code == 401


# ── Detections ───────────────────────────────────────────────────────────────


def test_upload_creates_pending_detection(client, auth):
    image = upload(client, auth)

    res = client.get("/fetch/admin", headers=auth)
    assert res.get_json()["count"] == 1

    row = res.get_json()["data"][0]
    assert row == {
        "image_path": image,
        "date": row["date"],
        "time": row["time"],
        "location": "Gota",
        "mac_address": "AA:BB:CC",
        "approved": 0,
    }


def test_upload_requires_file(client, auth):
    assert client.post("/add/Gota/AA", headers=auth, data={}).status_code == 400


def test_area_filtering(client, auth):
    upload(client, auth, address="Gota")
    upload(client, auth, address="Bapunagar")

    assert client.get("/count/admin", headers=auth).get_json()["count"] == 2
    assert client.get("/count/Gota", headers=auth).get_json()["count"] == 1
    assert client.get("/count/Bopal", headers=auth).get_json()["count"] == 0


def test_verify_toggles_status(client, auth):
    image = upload(client, auth)

    assert client.post(f"/verify/{image}/Gota", headers=auth).status_code == 200
    assert client.get("/fetch/admin", headers=auth).get_json()["count"] == 0
    assert client.get("/fetchv/admin", headers=auth).get_json()["data"][0]["approved"] == 1

    client.post(f"/verify/{image}/Gota", headers=auth)
    assert client.get("/fetch/admin", headers=auth).get_json()["count"] == 1


def test_soft_delete_and_purge(client, auth):
    image = upload(client, auth)

    client.post(f"/temp_delete/{image}", headers=auth)
    assert client.get("/fetch_delete/admin", headers=auth).get_json()["data"][0]["image_path"] == image
    assert client.get("/fetch/admin", headers=auth).get_json()["count"] == 0

    assert client.post("/delete_all", headers=auth).status_code == 200
    assert client.get("/fetch_all", headers=auth).get_json()["count"] == 0


def test_hard_delete(client, auth):
    image = upload(client, auth)

    assert client.post(f"/delete_row/{image}", headers=auth).status_code == 200
    assert client.get("/fetch_all", headers=auth).get_json()["count"] == 0
    assert client.post("/delete_row/nope.jpg", headers=auth).status_code == 404


def test_media_is_served(client, auth, account):
    image = upload(client, auth)

    assert client.get(f"/media/{image}").status_code == 401
    assert client.get(f"/media/{image}?token={account['token']}").data == b"fake-jpeg"
    assert client.get(f"/media/{image}", headers=auth).data == b"fake-jpeg"


# ── Защита от SQL-инъекций ───────────────────────────────────────────────────


def test_sql_injection_in_login_is_inert(client, auth):
    res = client.post("/login", json={"username": "admin' OR '1'='1", "password": "x"})
    assert res.status_code == 401


def test_sql_injection_in_area_is_inert(client, auth):
    upload(client, auth, address="Gota")
    res = client.get("/fetch/Gota' OR '1'='1", headers=auth)
    assert res.status_code == 200
    assert res.get_json()["count"] == 0
