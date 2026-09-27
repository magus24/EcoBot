"""Слой доступа к данным: подключение к SQLite и схема таблиц."""

import sqlite3
from contextlib import contextmanager

from config import Config

# Статусы записи о detections:
#   0 — новая, ожидает проверки оператором
#   1 — подтверждена оператором
#   2 — помечена как удалённая (soft delete)
STATUS_NEW = 0
STATUS_VERIFIED = 1
STATUS_DELETED = 2

SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS detections (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        image        TEXT    NOT NULL UNIQUE,
        date         TEXT    NOT NULL,
        time         TEXT    NOT NULL,
        address      TEXT,
        mac_address  TEXT,
        is_verified  INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        username      TEXT PRIMARY KEY,
        email         TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL
    )
    """,
)


@contextmanager
def get_db():
    """Контекстный менеджер, отдающий соединение с включённым row_factory."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Создаёт каталог для загрузок и таблицы, если их ещё нет."""
    Config.ensure_dirs()
    with get_db() as conn:
        for statement in SCHEMA:
            conn.execute(statement)


def serialize_detection(row: sqlite3.Row) -> dict:
    """Приводит строку таблицы `detections` к формату, который ждёт фронтенд."""
    return {
        "image_path": row["image"],
        "date": row["date"],
        "time": row["time"],
        "location": row["address"],
        "mac_address": row["mac_address"],
        "approved": row["is_verified"],
    }
