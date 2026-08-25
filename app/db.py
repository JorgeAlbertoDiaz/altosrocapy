"""Portable SQLite database access for AltosRoca."""

import os
import sqlite3
import sys


def get_db_path() -> str:
    """Resolve the DB path so the app is 100% portable.

    Frozen (PyInstaller): <exe dir>/data/altosroca.db
    Dev:                  <project root>/data/altosroca.db
    """
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "data", "altosroca.db")


def get_connection() -> sqlite3.Connection:
    path = get_db_path()
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Base de datos no encontrada en: {path}"
        )
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def validate_credentials(username: str, password: str) -> bool:
    """Check credentials against the legacy Login table.

    NOTE: the legacy DB stores passwords in plain text; this must be
    improved (hashing) before any real deployment.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM Login WHERE UserName = ? AND Password = ?",
            (username, password),
        ).fetchone()
        return row is not None
    finally:
        conn.close()
