"""Database schema migrations, applied in order by Core."""

# The initial schema; docs/data-model.md shows the schema after all migrations.
# IF NOT EXISTS / OR IGNORE make a rerun a no-op; with the atomic runner in
# Core._migrate, new migrations don't need to be rerun-safe.
_MIGRATION_V1 = """
CREATE TABLE IF NOT EXISTS projects (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE CHECK (name <> '')
) STRICT;

-- Singleton app state. default_project_id is NOT NULL with no ON DELETE action, so a
-- default project always exists and deleting it is refused by the database itself.
-- selected_project_id is the persisted UI project filter; deleting that project resets it.
-- theme has no CHECK: valid names come from the UI framework and change across its
-- versions; the TUI validates the value and falls back to its default.
CREATE TABLE IF NOT EXISTS app_state (
    id                  INTEGER PRIMARY KEY CHECK (id = 1),
    default_project_id  INTEGER NOT NULL REFERENCES projects(id),
    selected_project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    theme               TEXT NOT NULL DEFAULT 'textual-dark'
) STRICT;

CREATE TABLE IF NOT EXISTS tasks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title      TEXT NOT NULL CHECK (title <> ''),
    body       TEXT,
    status     TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'doing', 'done')),
    priority   TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    done_at    INTEGER,
    CHECK ((status = 'done') = (done_at IS NOT NULL))
) STRICT;

CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

-- Readable listing for manual DB inspection; the application does not use it.
CREATE VIEW IF NOT EXISTS tasks_v AS
SELECT t.id, p.name AS project, t.status, t.priority, t.title, t.created_at, t.done_at
FROM tasks t JOIN projects p ON p.id = t.project_id;

-- Seed: a fresh database always starts with one project, which is the default.
INSERT OR IGNORE INTO projects (name) VALUES ('inbox');
INSERT OR IGNORE INTO app_state (id, default_project_id) SELECT 1, id FROM projects WHERE name = 'inbox';
"""

_MIGRATION_V2 = """
ALTER TABLE app_state ADD COLUMN show_preview INTEGER NOT NULL DEFAULT 0 CHECK (show_preview IN (0, 1));
"""

MIGRATIONS = (_MIGRATION_V1, _MIGRATION_V2)  # append-only; index+1 = PRAGMA user_version
