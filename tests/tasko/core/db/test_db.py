"""Database bootstrap: fresh databases, reopening, and upgrades of older ones."""

import re
import sqlite3

from tasko.core.db.db import open_db
from tasko.core.db.migrations import MIGRATIONS


def query(db_path, sql):
    """Run a read-only query over a separate plain connection."""
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def contents(db_path):
    """Every schema object's SQL without comments and whitespace, and every table's rows."""
    objects = query(db_path, "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")
    sql = {name: re.sub(r"--[^\n]*|\s+", "", text) for _, name, text in objects}
    rows = {name: query(db_path, f"SELECT * FROM {name}") for kind, name, _ in objects if kind == "table"}
    return sql, rows


class TestMigrations:
    """Schema versioning via PRAGMA user_version."""

    def test_fresh_database(self, tmp_path):
        """A new database gets the full schema, the seed project, and the final version."""
        db = tmp_path / "tasko.db"
        open_db(db).close()
        assert query(db, "PRAGMA user_version") == [(len(MIGRATIONS),)]
        assert query(db, "SELECT name FROM projects") == [("inbox",)]
        (default_id,) = query(db, "SELECT default_project_id FROM app_state")[0]
        assert query(db, "SELECT id FROM projects WHERE name = 'inbox'") == [(default_id,)]

    def test_reopen_is_noop(self, tmp_path):
        """Opening an up-to-date database changes nothing."""
        db = tmp_path / "tasko.db"
        open_db(db).close()
        open_db(db).close()
        assert query(db, "PRAGMA user_version") == [(len(MIGRATIONS),)]
        assert query(db, "SELECT count(*) FROM projects") == [(1,)]

    def test_upgrade_matches_fresh(self, tmp_path):
        """A v1 database brought up by every later migration equals one made from the full schema.

        The stored SQL is compared as text, so CHECKs, STRICT, defaults, views, and column order all count.
        """
        fresh, upgraded = tmp_path / "fresh.db", tmp_path / "upgraded.db"
        open_db(fresh).close()
        conn = sqlite3.connect(upgraded)
        conn.executescript(f"{MIGRATIONS[0]}\nPRAGMA user_version = 1;")
        conn.close()
        open_db(upgraded).close()
        assert query(upgraded, "PRAGMA user_version") == [(len(MIGRATIONS),)]
        assert contents(upgraded) == contents(fresh)
