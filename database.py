"""
SQLite database layer for scambaiter.
Manages scammer profiles and conversation history.
"""

import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "scambaiter.db"


def get_conn() -> sqlite3.Connection:
    """Create a new database connection with Row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables and indexes if they don't exist. Called once at startup."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS scammers (
                user_id       INTEGER PRIMARY KEY,
                username      TEXT,
                display_name  TEXT,
                first_seen    DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen     DATETIME DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                status        TEXT DEFAULT 'active'
            );

            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                role        TEXT NOT NULL,
                content     TEXT NOT NULL,
                timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
                llm_model   TEXT,
                latency_ms  INTEGER,
                FOREIGN KEY (user_id) REFERENCES scammers(user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id);
            CREATE INDEX IF NOT EXISTS idx_messages_ts   ON messages(timestamp);
        """)


def upsert_scammer(user_id: int, username: str | None, display_name: str | None) -> None:
    """
    Insert or update a scammer record.
    On conflict: update username, display_name, last_seen, increment message_count.
    """
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO scammers (user_id, username, display_name, message_count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                display_name = excluded.display_name,
                last_seen = CURRENT_TIMESTAMP,
                message_count = scammers.message_count + 1
        """, (user_id, username, display_name))


def save_message(
    user_id: int,
    role: str,
    content: str,
    model: str | None = None,
    latency_ms: int | None = None
) -> None:
    """Insert a message row into the messages table."""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO messages (user_id, role, content, llm_model, latency_ms)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, role, content, model, latency_ms))


def get_history(user_id: int, limit: int) -> list[dict[str, Any]]:
    """
    Return last `limit` messages as [{"role": ..., "content": ...}].
    Ordered oldest-first for LLM context.
    """
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT role, content
            FROM messages
            WHERE user_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
        """, (user_id, limit)).fetchall()

    return [{"role": r["role"], "content": r["content"]} for r in rows]


def get_all_scammers() -> list[dict[str, Any]]:
    """
    Return all scammers joined with their latest message timestamp.
    Ordered by most recent activity (last_seen).
    """
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT
                s.user_id,
                s.username,
                s.display_name,
                s.first_seen,
                s.last_seen,
                s.message_count,
                s.status,
                MAX(m.timestamp) as latest_message
            FROM scammers s
            LEFT JOIN messages m ON s.user_id = m.user_id
            GROUP BY s.user_id
            ORDER BY s.last_seen DESC
        """).fetchall()

    return [dict(r) for r in rows]
