"""Migration bootstrap: fresh databases, reopening, and crash recovery."""

import sqlite3

from tasko.core.core import Core
from tasko.core.migrations import MIGRATIONS


def query(db_path, sql):
    """Run a read-only query over a separate plain connection."""
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


class TestMigrations:
    """Schema versioning via PRAGMA user_version."""

    def test_fresh_database(self, tmp_path):
        """A new database gets the full schema, the seed project, and the final version."""
        db = tmp_path / "tasko.db"
        Core(db).close()
        assert query(db, "PRAGMA user_version") == [(len(MIGRATIONS),)]
        assert query(db, "SELECT name FROM projects") == [("inbox",)]
        (default_id,) = query(db, "SELECT default_project_id FROM app_state")[0]
        assert query(db, "SELECT id FROM projects WHERE name = 'inbox'") == [(default_id,)]

    def test_reopen_is_noop(self, tmp_path):
        """Opening an up-to-date database changes nothing."""
        db = tmp_path / "tasko.db"
        Core(db).close()
        Core(db).close()
        assert query(db, "PRAGMA user_version") == [(len(MIGRATIONS),)]
        assert query(db, "SELECT count(*) FROM projects") == [(1,)]

    def test_recovers_from_interrupted_migration(self, tmp_path):
        """A crash between executescript and the version bump must not break the next start."""
        db = tmp_path / "tasko.db"
        conn = sqlite3.connect(db)
        conn.executescript(MIGRATIONS[0])  # apply v1 but leave user_version at 0
        conn.commit()
        conn.close()
        Core(db).close()  # reruns v1; IF NOT EXISTS / OR IGNORE must make it a no-op
        assert query(db, "PRAGMA user_version") == [(len(MIGRATIONS),)]
        assert query(db, "SELECT count(*) FROM projects") == [(1,)]
