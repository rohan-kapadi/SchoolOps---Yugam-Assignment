"""SQLite connection and transaction management for SchoolOps AI."""

from contextlib import contextmanager
import sqlite3
from typing import Generator

from agent_api.config import DB_PATH
from agent_api.database.models import CREATE_TABLES_SQL


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Return a configured sqlite3 connection with Row factory enabled."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str | None = None) -> None:
    """Initialize database tables and constraints if they do not exist."""
    with get_connection(db_path) as conn:
        conn.executescript(CREATE_TABLES_SQL)
        conn.commit()


@contextmanager
def db_session(db_path: str | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager yielding a database connection with auto-commit and rollback."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
