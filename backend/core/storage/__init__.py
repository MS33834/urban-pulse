"""
Urban Pulse — SQLite storage layer.

Singleton database instance with auto-init tables.
"""

import logging
import os
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

# Default: <project_root>/data/urban_pulse.db
_DEFAULT_DB_PATH = os.getenv(
    "URBAN_PULSE_DB",
    str(Path(__file__).parent.parent.parent.parent / "data" / "urban_pulse.db"),
)

_connection: sqlite3.Connection | None = None


def get_db_path() -> str:
    return _DEFAULT_DB_PATH


def get_connection() -> sqlite3.Connection:
    """Return the singleton database connection (thread-shared, WAL mode)."""
    global _connection
    if _connection is None:
        db_path = get_db_path()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        _connection = sqlite3.connect(db_path, check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA journal_mode=WAL")
        _connection.execute("PRAGMA foreign_keys=ON")
        logger.info("SQLite database opened: %s", db_path)
    return _connection


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS datasets (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            description TEXT DEFAULT '',
            source      TEXT,
            row_count   INTEGER DEFAULT 0,
            col_count   INTEGER DEFAULT 0,
            has_time_dim INTEGER DEFAULT 0,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS dataset_columns (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id      TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
            col_name        TEXT NOT NULL,
            col_index       INTEGER NOT NULL,
            detected_role   TEXT,         -- entity | time | indicator | categorical
            data_type       TEXT,         -- number | text
            human_label     TEXT,
            UNIQUE(dataset_id, col_name)
        );

        CREATE TABLE IF NOT EXISTS records (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id  TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
            entity      TEXT NOT NULL,
            year        INTEGER,          -- NULL if no time dimension
            indicator   TEXT NOT NULL,
            value       REAL
        );

        CREATE INDEX IF NOT EXISTS idx_records_dataset
            ON records(dataset_id);
        CREATE INDEX IF NOT EXISTS idx_records_lookup
            ON records(dataset_id, entity, year);
        CREATE INDEX IF NOT EXISTS idx_records_indicator
            ON records(dataset_id, indicator);
    """)
    conn.commit()
    logger.info("Database tables initialized")


def close_db() -> None:
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
        logger.info("Database connection closed")
