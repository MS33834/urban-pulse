"""
Urban Pulse — SQLite storage layer.

Singleton database instance with auto-init tables.
"""

import logging
import os
import sqlite3
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

# Default: <project_root>/data/urban_pulse.db
_DEFAULT_DB_PATH = os.getenv(
    "URBAN_PULSE_DB",
    str(Path(__file__).parent.parent.parent.parent / "data" / "urban_pulse.db"),
)

_connection: sqlite3.Connection | None = None
_lock = threading.Lock()


def get_db_path() -> str:
    return _DEFAULT_DB_PATH


def get_connection() -> sqlite3.Connection:
    """Return the singleton database connection (thread-shared, WAL mode).

    SQLite 在 check_same_thread=False 下允许跨线程使用同一连接,
    但写操作仍需串行化。这里用全局锁保护所有写入路径,
    避免并发写触发 "database is locked" 错误。
    """
    global _connection
    if _connection is None:
        with _lock:
            if _connection is None:
                db_path = get_db_path()
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                conn = sqlite3.connect(db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                # WAL 模式:读写不互斥,适合一写多读的 Web 场景
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA foreign_keys=ON")
                # 5s 忙等待,避免短暂锁冲突直接抛错
                conn.execute("PRAGMA busy_timeout=5000")
                # 正常同步级别:WAL 下 fsync 只作用于 WAL,性能可接受
                conn.execute("PRAGMA synchronous=NORMAL")
                _connection = conn
                logger.info("SQLite database opened: %s", db_path)
    return _connection


def execute_write(sql: str, params: tuple | list = ()) -> sqlite3.Cursor:
    """串行化写入入口,所有 INSERT/UPDATE/DELETE 应走这里。"""
    conn = get_connection()
    with _lock:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur


def executescript_write(script: str) -> None:
    """串行化 executescript,用于建表等 DDL。"""
    conn = get_connection()
    with _lock:
        conn.executescript(script)
        conn.commit()


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = get_connection()
    with _lock:
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
            -- 覆盖 ORDER BY entity, year, indicator 的查询
            CREATE INDEX IF NOT EXISTS idx_records_order
                ON records(dataset_id, entity, year, indicator);
            -- dataset_columns 按 col_index 排序查询
            CREATE INDEX IF NOT EXISTS idx_columns_dataset_idx
                ON dataset_columns(dataset_id, col_index);
            -- datasets 按创建时间倒序列表
            CREATE INDEX IF NOT EXISTS idx_datasets_created
                ON datasets(created_at DESC);
        """)
        conn.commit()
    logger.info("Database tables initialized")


def close_db() -> None:
    global _connection
    with _lock:
        if _connection is not None:
            _connection.close()
            _connection = None
            logger.info("Database connection closed")
