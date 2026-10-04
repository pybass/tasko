"""The full current schema of the database, written as if the database were made from scratch.

A new database is made from SCHEMA at the latest version. Every schema change edits it and adds a migration that
brings older databases to the same result: the same tables with columns in the same order, constraints, indexes,
views, and seed rows.
"""

# Timestamps are unix seconds. Foreign keys are enforced only under PRAGMA foreign_keys = ON, which is
# per-connection and OFF by default; open_db turns it on.
SCHEMA = """
CREATE TABLE projects (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE CHECK (name <> '')
) STRICT;

-- Singleton app state: the CHECK pins the row id, so there is exactly one row.
CREATE TABLE app_state (
    id                  INTEGER PRIMARY KEY CHECK (id = 1),
    -- NOT NULL with no ON DELETE action: a default project always exists and the database refuses to delete it.
    default_project_id  INTEGER NOT NULL REFERENCES projects(id),
    -- The persisted UI project filter; deleting that project resets it to "all".
    selected_project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    -- No CHECK: valid names come from the UI framework and change across its versions; the TUI validates the
    -- value and falls back to its default.
    theme               TEXT NOT NULL DEFAULT 'textual-dark',
    -- Whether the task list shows the preview pane.
    show_preview        INTEGER NOT NULL DEFAULT 0 CHECK (show_preview IN (0, 1))
) STRICT;

CREATE TABLE tasks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title      TEXT NOT NULL CHECK (title <> ''),
    body       TEXT,
    status     TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'doing', 'done')),
    priority   TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,  -- equals created_at when never modified
    done_at    INTEGER,
    -- done_at is present exactly when the task is done: no half-closed states.
    CHECK ((status = 'done') = (done_at IS NOT NULL))
) STRICT;

CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_tasks_status ON tasks(status);

-- Readable listing for manual DB inspection (project names instead of ids); the application does not use it.
CREATE VIEW tasks_v AS
SELECT t.id, p.name AS project, t.status, t.priority, t.title, t.created_at, t.done_at
FROM tasks t JOIN projects p ON p.id = t.project_id;

-- Seed: a fresh database always starts with one project, which is the default.
INSERT INTO projects (name) VALUES ('inbox');
INSERT INTO app_state (id, default_project_id) SELECT 1, id FROM projects WHERE name = 'inbox';
"""
