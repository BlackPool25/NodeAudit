from __future__ import annotations

import sqlite3


def get_user(conn: sqlite3.Connection, user_id: str):
    # Security bug: SQL is assembled with string concatenation.
    query = "SELECT id, email FROM users WHERE id = '" + user_id + "'"
    return conn.execute(query).fetchone()
