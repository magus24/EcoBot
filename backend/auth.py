"""Аутентификация: хеширование паролей и токены сессии.

Пароли хранятся только в виде хеша (`werkzeug.security`). После успешного входа
клиент получает подписанный токен и передаёт его в заголовке
`Authorization: Bearer <token>` (или в query-параметре `token` — чтобы работали
обычные `<img src>`).
"""

import functools
import os

from flask import current_app, g, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

TOKEN_MAX_AGE = int(os.environ.get("ECOBOT_TOKEN_MAX_AGE", 60 * 60 * 12))
TOKEN_SALT = "ecobot-auth"


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=TOKEN_SALT)


def issue_token(username: str) -> str:
    return _serializer().dumps({"username": username})


def read_token(token: str):
    try:
        return _serializer().loads(token, max_age=TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def require_auth(view):
    """Пропускает запрос только с валидным токеном, иначе 401."""

    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            token = header[len("Bearer "):].strip()
        else:
            token = request.args.get("token", "")

        payload = read_token(token) if token else None
        if payload is None:
            return jsonify({"detail": "Missing or invalid token"}), 401

        g.username = payload["username"]
        return view(*args, **kwargs)

    return wrapper
