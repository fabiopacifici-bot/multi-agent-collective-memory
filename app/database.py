"""
Database initialization and connection management for the shared memory service.
Uses SQLite with WAL mode for concurrent reads.
"""

import sqlite3
import os
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DB_DIR / "memories.db"


def get_db_path() -> str:
    """Return the database file path, creating the directory if needed."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    return str(DB_PATH)


def get_connection() -> sqlite3.Connection:
    """Create a new SQLite connection with recommended settings."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    """Initialize the database schema. Idempotent — safe to call multiple times."""
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                agent       TEXT    NOT NULL,
                key         TEXT    UNIQUE NOT NULL,
                content_text TEXT   NOT NULL DEFAULT '',
                content_images TEXT NOT NULL DEFAULT '[]',
                embedding   BLOB,
                metadata    TEXT   NOT NULL DEFAULT '{}',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_memories_agent ON memories(agent);
            CREATE INDEX IF NOT EXISTS idx_memories_key   ON memories(key);
        """)
        conn.commit()
    finally:
        conn.close()
