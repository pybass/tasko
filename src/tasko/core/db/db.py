"""The connection setup and the migration runner; Core owns the queries."""

import sqlite3
from contextlib import ExitStack
from pathlib import Path

from tasko.core.db.migrations import MIGRATIONS
from tasko.core.db.schema import SCHEMA
from tasko.core.errors import AppError


def open_db(path: Path) -> sqlite3.Connection:
    """Open the database, creating the file and its directory if needed, and bring its schema to the latest version.

    Raises AppError if opening or preparing the database fails, including an unsupported schema version.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with ExitStack() as cleanup:
            conn = sqlite3.connect(path, autocommit=True)
            cleanup.callback(conn.close)
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
                raise AppError(f"{path} has schema v{version}, this tasko knows up to v{latest}: update tasko.")
            if version < latest:
                scripts = (SCHEMA,) if version == 0 else MIGRATIONS[version:]
                conn.executescript("\n".join(scripts) + f"\nPRAGMA user_version = {latest};")
            conn.execute("COMMIT")
            cleanup.pop_all()
    except (OSError, sqlite3.Error) as e:
        hint = ""
        if isinstance(e, (PermissionError, FileNotFoundError, NotADirectoryError)) or (
            isinstance(e, sqlite3.Error)
            and e.sqlite_errorcode & 0xFF in (sqlite3.SQLITE_CANTOPEN, sqlite3.SQLITE_READONLY, sqlite3.SQLITE_PERM)
        ):
            hint = (
                " Check the path and permissions."
                " Opening the database currently requires write access to the file and its directory."
            )
        raise AppError(f"Cannot open database '{path}': {e}.{hint}") from e
    return conn
