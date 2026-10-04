"""The connection setup and the migration runner; Core owns the queries."""

import sqlite3
from pathlib import Path

from tasko.core.db.migrations import MIGRATIONS
from tasko.core.db.schema import SCHEMA
from tasko.core.errors import AppError


def open_db(path: Path) -> sqlite3.Connection:
    """Open the database, creating the file and its directory if needed, and bring its schema to the latest version.

    Raises AppError for a database a newer tasko has migrated.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, autocommit=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")
    # The write lock is taken before the version is read, so a second process waits here and then sees the new
    # version. The scripts and the version bump commit together: a crash midway rolls back cleanly.
    conn.execute("BEGIN IMMEDIATE")
    version = int(conn.execute("PRAGMA user_version").fetchone()[0])  # 0 in a new database
    latest = len(MIGRATIONS)
    if version > latest:
        conn.close()
        raise AppError(f"{path} has schema v{version}, this tasko knows up to v{latest}: update tasko.")
    if version < latest:
        scripts = (SCHEMA,) if version == 0 else MIGRATIONS[version:]
        conn.executescript("\n".join(scripts) + f"\nPRAGMA user_version = {latest};")
    conn.execute("COMMIT")
    return conn
