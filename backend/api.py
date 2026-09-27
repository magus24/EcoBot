"""REST API EcoBot: приём кадров с камер, хранение и верификация detections.

Запуск:
    python api.py            # http://127.0.0.1:5000
    PORT=8080 python api.py

Все маршруты, кроме /health и /login, требуют заголовок
`Authorization: Bearer <token>` (см. auth.require_auth). Для `<img src>` токен
можно передать query-параметром: `/media/<file>?token=<token>`.
"""

import os
from datetime import datetime
from uuid import uuid4

from flask import Flask, g, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from auth import hash_password, issue_token, require_auth, verify_password
from config import Config
from db import (
    STATUS_DELETED,
    STATUS_NEW,
    STATUS_VERIFIED,
    get_db,
    init_db,
    serialize_detection,
)

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)


def _where(area: str, status: int):
    """`admin` видит все записи, остальные — только свой участок."""
    conditions, params = [], []
    if area != "admin":
        conditions.append("address = ?")
        params.append(area)
    conditions.append("is_verified = ?")
    params.append(status)
    return " WHERE " + " AND ".join(conditions), tuple(params)


def _fetch(area: str, status: int):
    where, params = _where(area, status)
    query = "SELECT * FROM detections" + where + " ORDER BY date DESC, time DESC"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()

    return jsonify({"data": [serialize_detection(row) for row in rows],
                    "count": len(rows)})


def _current_status(image: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT is_verified FROM detections WHERE image = ?", (image,)
        ).fetchone()
    return None if row is None else row["is_verified"]


# ── Служебное ────────────────────────────────────────────────────────────────


@app.get("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat(timespec="seconds")})


# ── Пользователи и вход ──────────────────────────────────────────────────────


@app.post("/users")
def create_user():
    """Регистрация. Если пользователей ещё нет — любой может создать первый аккаунт."""
    payload = request.get_json(silent=True) or request.form
    username = (payload.get("username") or "").strip()
    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""

    if not username or not email or not password:
        return jsonify({"detail": "username, email and password are required"}), 400

    with get_db() as conn:
        if conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"] > 0:
            return jsonify({"detail": "Registration is closed, ask an existing user"}), 403
        if conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
            return jsonify({"detail": "Username already taken"}), 409
        conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, hash_password(password)),
        )

    return jsonify({"detail": "User created", "username": username}), 201


@app.delete("/users/<username>")
@require_auth
def delete_user(username):
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM users WHERE username = ?", (username,))
    if cursor.rowcount == 0:
        return jsonify({"detail": f"Unknown user {username}"}), 404
    return jsonify({"detail": f"User {username} deleted"})


@app.post("/login")
def login():
    """`{"username": "...", "password": "..."}` -> профиль + токен."""
    payload = request.get_json(silent=True) or request.form
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    with get_db() as conn:
        row = conn.execute(
            "SELECT username, password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()

    if row is None or not verify_password(row["password_hash"], password):
        return jsonify({"Username": "", "status": "No"}), 401

    return jsonify(
        {
            "Username": row["username"],
            "status": "Yes",
            "isAdmin": row["username"] == "admin",
            "token": issue_token(row["username"]),
        }
    )


@app.get("/valid/<name>/<passw>")
def login_legacy(name, passw):
    """Устаревший вход через URL. Оставлен для совместимости, пароль в URL небезопасен."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT username, password_hash FROM users WHERE username = ?", (name,)
        ).fetchone()

    if row is None or not verify_password(row["password_hash"], passw):
        return jsonify({"Username": "", "status": "No"}), 401

    return jsonify(
        {
            "Username": row["username"],
            "status": "Yes",
            "isAdmin": row["username"] == "admin",
            "token": issue_token(row["username"]),
        }
    )


# ── Приём кадров с камер ────────────────────────────────────────────────────


@app.post("/add/<addr>/<mac>")
@require_auth
def add_detection(addr, mac):
    """Приём кадра: multipart/form-data, поле `file`."""
    upload = request.files.get("file")
    if upload is None or upload.filename == "":
        return jsonify({"detail": "No image selected."}), 400

    filename = (
        f"{datetime.now().strftime('%Y%m%d%H%M%S')}_"
        f"{uuid4().hex[:8]}_{secure_filename(upload.filename)}"
    )
    upload.save(os.path.join(Config.UPLOAD_FOLDER, filename))

    now = datetime.now()
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO detections
               (image, date, time, address, mac_address, is_verified)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (filename, now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"),
             addr, mac, STATUS_NEW),
        )

    return jsonify({"detail": "Image has been successfully uploaded",
                    "image": filename}), 201


@app.get("/media/<path:image>")
@require_auth
def media(image):
    """Раздача сохранённых кадров.

    Токен здесь допустимо передать query-параметром (`/media/<file>?token=...`),
    потому что `<img src>` не умеет слать заголовки.
    """
    return send_from_directory(Config.UPLOAD_FOLDER, image)


# ── Выборка detections ──────────────────────────────────────────────────────


@app.get("/fetch/<area>")
@require_auth
def fetch_pending(area):
    """Новые detections, ожидающие проверки."""
    return _fetch(area, STATUS_NEW)


@app.get("/fetchv/<area>")
@require_auth
def fetch_verified(area):
    """Подтверждённые detections."""
    return _fetch(area, STATUS_VERIFIED)


@app.get("/fetch_delete/<area>")
@require_auth
def fetch_deleted(area):
    """Удалённые detections (soft delete)."""
    return _fetch(area, STATUS_DELETED)


@app.get("/fetch_all")
@require_auth
def fetch_all():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM detections ORDER BY date DESC, time DESC").fetchall()
    return jsonify({"data": [serialize_detection(row) for row in rows],
                    "count": len(rows)})


@app.get("/count/<area>")
@require_auth
def count(area):
    where, params = _where(area, STATUS_NEW)
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM detections" + where, params).fetchone()["c"]
    return jsonify({"count": total})


# ── Действия оператора ──────────────────────────────────────────────────────


def _set_status(image, new_status):
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE detections SET is_verified = ? WHERE image = ?", (new_status, image)
        )
    if cursor.rowcount == 0:
        return jsonify({"detail": f"Unknown detection {image}"}), 404
    return jsonify({"detail": f"Detection {image} moved to status {new_status}"})


@app.post("/verify/<image>/<area>")
@require_auth
def verify(image, area):
    """Переключает статус 0 <-> 1 (новое <-> подтверждено)."""
    current = _current_status(image)
    if current is None:
        return jsonify({"detail": f"Unknown detection {image}"}), 404
    return _set_status(image, STATUS_NEW if current == STATUS_VERIFIED else STATUS_VERIFIED)


@app.post("/temp_delete/<image>")
@require_auth
def temp_delete(image):
    """Переключает статус 0 <-> 2 (новое <-> удалено)."""
    current = _current_status(image)
    if current is None:
        return jsonify({"detail": f"Unknown detection {image}"}), 404
    return _set_status(image, STATUS_NEW if current == STATUS_DELETED else STATUS_DELETED)


@app.post("/delete_row/<image>")
@require_auth
def delete_row(image):
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM detections WHERE image = ?", (image,))
    if cursor.rowcount == 0:
        return jsonify({"detail": f"Unknown detection {image}"}), 404
    return jsonify({"detail": f"Detection {image} deleted permanently"})


@app.post("/delete_all")
@require_auth
def delete_all():
    """Окончательно удаляет все записи, помеченные как удалённые."""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM detections WHERE is_verified = ?", (STATUS_DELETED,))
    return jsonify({"detail": f"{cursor.rowcount} detections deleted permanently"})


@app.get("/whoami")
@require_auth
def whoami():
    return jsonify({"Username": g.username})


init_db()

if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
    )
