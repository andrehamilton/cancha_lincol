"""Acceso local SQLite para las cuentas de usuario."""

import hashlib
import hmac
import secrets
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "cancha_users.db"


def _connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with _connect() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                reset_code TEXT,
                verified INTEGER NOT NULL DEFAULT 0,
                verification_code TEXT
            )
        """)
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)")}
        if "verified" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN verified INTEGER NOT NULL DEFAULT 1")
        if "verification_code" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN verification_code TEXT")


def _hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 bytes.fromhex(salt), 200_000).hex()
    return salt, digest


def create_pending_user(full_name, email, password):
    code = f"{secrets.randbelow(1_000_000):06d}"
    salt, password_hash = _hash_password(password)
    try:
        with _connect() as connection:
            connection.execute(
                "INSERT INTO users(full_name, email, salt, password_hash, verification_code) "
                "VALUES (?, ?, ?, ?, ?)",
                (full_name.strip(), email.strip().lower(), salt, password_hash, code),
            )
    except sqlite3.IntegrityError as error:
        raise ValueError("Ya existe una cuenta con ese correo.") from error
    return code


def refresh_pending_user(full_name, email, password):
    code = f"{secrets.randbelow(1_000_000):06d}"
    salt, password_hash = _hash_password(password)
    with _connect() as connection:
        cursor = connection.execute(
            "UPDATE users SET full_name = ?, salt = ?, password_hash = ?, verification_code = ? "
            "WHERE email = ? COLLATE NOCASE AND verified = 0",
            (full_name.strip(), salt, password_hash, code, email.strip()),
        )
    if not cursor.rowcount:
        raise ValueError("Ese correo ya tiene una cuenta activa o no se pudo actualizar.")
    return code


def verify_user(email, code):
    with _connect() as connection:
        cursor = connection.execute(
            "UPDATE users SET verified = 1, verification_code = NULL "
            "WHERE email = ? COLLATE NOCASE AND verification_code = ? AND verified = 0",
            (email.strip(), code.strip()),
        )
    return cursor.rowcount > 0


def delete_pending_user(email, code):
    with _connect() as connection:
        connection.execute(
            "DELETE FROM users WHERE email = ? COLLATE NOCASE AND verification_code = ? AND verified = 0",
            (email.strip(), code.strip()),
        )


def authenticate(email, password):
    with _connect() as connection:
        user = connection.execute(
            "SELECT id, full_name, salt, password_hash, verified FROM users WHERE email = ? COLLATE NOCASE",
            (email.strip(),),
        ).fetchone()
    if user is None:
        return None
    _, candidate = _hash_password(password, user["salt"])
    if not hmac.compare_digest(candidate, user["password_hash"]):
        return None
    return {"unverified": True} if not user["verified"] else dict(user)


def create_reset_code(email):
    code = f"{secrets.randbelow(1_000_000):06d}"
    with _connect() as connection:
        cursor = connection.execute(
            "UPDATE users SET reset_code = ? WHERE email = ? COLLATE NOCASE",
            (code, email.strip()),
        )
    return code if cursor.rowcount else None


def clear_reset_code(email, code):
    with _connect() as connection:
        connection.execute(
            "UPDATE users SET reset_code = NULL WHERE email = ? COLLATE NOCASE AND reset_code = ?",
            (email.strip(), code),
        )


def reset_password(email, code, new_password):
    salt, password_hash = _hash_password(new_password)
    with _connect() as connection:
        cursor = connection.execute(
            "UPDATE users SET salt = ?, password_hash = ?, reset_code = NULL "
            "WHERE email = ? COLLATE NOCASE AND reset_code = ?",
            (salt, password_hash, email.strip(), code.strip()),
        )
    return cursor.rowcount > 0


def update_pending_password(email, code, new_password):
    salt, password_hash = _hash_password(new_password)
    with _connect() as connection:
        cursor = connection.execute(
            "UPDATE users SET salt = ?, password_hash = ?, verified = 1, verification_code = NULL "
            "WHERE email = ? COLLATE NOCASE AND verification_code = ? AND verified = 0",
            (salt, password_hash, email.strip(), code.strip()),
        )
    return cursor.rowcount > 0
