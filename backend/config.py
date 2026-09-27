"""Конфигурация Flask-приложения EcoBot.

Все пути по умолчанию считаются от каталога `backend/`, поэтому приложение
можно запускать из любого рабочего каталога. Значения переопределяются
переменными окружения (см. `.env.example`).
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _path_from_env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return os.path.abspath(value) if value else default


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # SQLite-база с detections и пользователями.
    DATABASE_PATH = _path_from_env("DATABASE_PATH", os.path.join(BASE_DIR, "ecobot.db"))

    # Каталог для загруженных кадров (отдаётся через /media/<file>).
    UPLOAD_FOLDER = _path_from_env("UPLOAD_FOLDER", os.path.join(BASE_DIR, "media"))

    @classmethod
    def ensure_dirs(cls) -> None:
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
