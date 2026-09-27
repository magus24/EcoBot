"""Небольшой CLI для управления пользователями.

    python manage.py create-user            # спросит имя и пароль
    python manage.py create-user admin ops@city.gov --password secret
    python manage.py list-users
    python manage.py reset-password admin
"""

import argparse
import getpass
import sys

from auth import hash_password
from db import get_db, init_db


def create_user(args) -> int:
    username = args.username
    email = args.email or f"{username}@ecobot.local"
    password = args.password or getpass.getpass(f"Пароль для {username}: ")

    if not password:
        print("Пароль не может быть пустым.", file=sys.stderr)
        return 1

    with get_db() as conn:
        try:
            conn.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, hash_password(password)),
            )
        except Exception as exc:  # UNIQUE constraint
            print(f"Не удалось создать пользователя: {exc}", file=sys.stderr)
            return 1

    print(f"Пользователь {username} <{email}> создан.")
    return 0


def reset_password(args) -> int:
    password = args.password or getpass.getpass(f"Новый пароль для {args.username}: ")
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (hash_password(password), args.username),
        )
    if cursor.rowcount == 0:
        print(f"Пользователь {args.username} не найден.", file=sys.stderr)
        return 1
    print(f"Пароль {args.username} обновлён.")
    return 0


def list_users(_args) -> int:
    with get_db() as conn:
        rows = conn.execute("SELECT username, email FROM users ORDER BY username").fetchall()
    if not rows:
        print("Пользователей нет.")
        return 0
    for row in rows:
        print(f"{row['username']:<20} {row['email']}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="EcoBot user management")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-user", help="создать пользователя")
    create.add_argument("username")
    create.add_argument("email", nargs="?")
    create.add_argument("--password", "-p")
    create.set_defaults(func=create_user)

    reset = sub.add_parser("reset-password", help="сменить пароль")
    reset.add_argument("username")
    reset.add_argument("--password", "-p")
    reset.set_defaults(func=reset_password)

    listing = sub.add_parser("list-users", help="показать пользователей")
    listing.set_defaults(func=list_users)

    args = parser.parse_args(argv)
    init_db()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
