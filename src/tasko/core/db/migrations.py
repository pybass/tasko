"""The migrations that bring an older database to the latest schema version.

This file is append-only. A released migration never changes: databases already ran it, and a changed script would
describe a step no database took. A mistake is fixed by a new migration. A migration that changes the schema comes
with the same change to the full schema in schema.py, which new databases are made from.
"""

# The starting schema, which every later migration changes. open_db never runs it: no database is older than v1,
# and a new one is made from the full schema, where the tables and columns are explained.
_MIGRATION_V1 = """
CREATE TABLE projects (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE CHECK (name <> '')
) STRICT;

CREATE TABLE app_state (
    id                  INTEGER PRIMARY KEY CHECK (id = 1),
    default_project_id  INTEGER NOT NULL REFERENCES projects(id),
    selected_project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    theme               TEXT NOT NULL DEFAULT 'textual-dark',
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
    updated_at INTEGER NOT NULL,
    done_at    INTEGER,
    CHECK ((status = 'done') = (done_at IS NOT NULL))
) STRICT;

CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_tasks_status ON tasks(status);

CREATE VIEW tasks_v AS
SELECT t.id, p.name AS project, t.status, t.priority, t.title, t.created_at, t.done_at
FROM tasks t JOIN projects p ON p.id = t.project_id;

INSERT INTO projects (name) VALUES ('inbox');
INSERT INTO app_state (id, default_project_id) SELECT 1, id FROM projects WHERE name = 'inbox';
"""

MIGRATIONS = (_MIGRATION_V1,)  # append-only; index+1 = PRAGMA user_version
