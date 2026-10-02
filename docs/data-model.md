# Data Model

## Entities

Two entity tables — `projects` and `tasks` — plus `app_state`, a singleton row
holding application-level state: the default project, the persisted project
filter, and the UI theme.

## Full schema (SQL)

```sql
-- SQLite. Note: PRAGMA foreign_keys is per-connection and OFF by default —
-- the application must enable it on every connection.
PRAGMA foreign_keys = ON;

CREATE TABLE projects (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE CHECK (name <> '')
) STRICT;

-- Singleton app state (the CHECK pins the row id, so there is exactly one row):
--   * default_project_id — NOT NULL + FK with no ON DELETE action: a default
--     project always exists and the database refuses to delete it;
--   * selected_project_id — the persisted UI project filter: deleting the
--     selected project resets the filter to "all" via ON DELETE SET NULL;
--   * theme — the persisted UI theme name.
CREATE TABLE app_state (
    id                  INTEGER PRIMARY KEY CHECK (id = 1),
    default_project_id  INTEGER NOT NULL REFERENCES projects(id),
    selected_project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    theme               TEXT NOT NULL DEFAULT 'textual-dark'
) STRICT;

CREATE TABLE tasks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title      TEXT NOT NULL CHECK (title <> ''),
    body       TEXT,                            -- optional long description
    status     TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'doing', 'done')),
    priority   TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    created_at INTEGER NOT NULL,                -- unix seconds
    updated_at INTEGER NOT NULL,                -- equals created_at when never modified
    done_at    INTEGER,                         -- unix seconds, set when status becomes 'done'
    -- done_at is present exactly when the task is done — no half-closed states.
    CHECK ((status = 'done') = (done_at IS NOT NULL))
) STRICT;

CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_tasks_status ON tasks(status);

-- Readable listing for manual DB inspection (shows project names instead of ids);
-- the application does not use it.
CREATE VIEW tasks_v AS
SELECT t.id, p.name AS project, t.status, t.priority, t.title, t.created_at, t.done_at
FROM tasks t JOIN projects p ON p.id = t.project_id;

-- Seed: a fresh database always starts with one project, which is the default.
INSERT INTO projects (name) VALUES ('inbox');
INSERT INTO app_state (id, default_project_id) SELECT 1, id FROM projects WHERE name = 'inbox';
```

## Invariants & conventions

- **Every task belongs to a project** — `project_id` is `NOT NULL`; listing
  and filtering never deal with orphans.
- **Exactly one default project** — a task added with no project given
  always has a target. The default is a pointer in `app_state`:
  `NOT NULL` plus an FK with no `ON DELETE` action make "zero defaults" and
  "delete the default project" impossible at the database level. Any project
  can be made the default.
- **TUI quick capture lands in the visible list** — the target is
  `selected ?? default`, so a new task appears in the list the user is
  looking at. `ON DELETE SET NULL` resets the filter to "all" when the
  selected project is deleted. The CLI `add` without `-p` always uses the
  default project: the TUI filter must not steer a script.
- **At least one project always exists** — the default exists and cannot be
  deleted, so the project count never reaches zero.
- **Deleting a project deletes its tasks** — `ON DELETE CASCADE`; deleting
  the last remaining project is refused in the application layer.
- **done ⇔ done_at** — the invariant lives in a schema CHECK, not in code
  discipline.
- **Statuses: `todo → doing → done`** — a single enum; more states can be
  added later via migration.
- **Ids are never reused** — `AUTOINCREMENT`; short integer ids read well in
  the TUI table.
- **Timestamps are unix seconds.**
- **STRICT tables** — column types are enforced, not advisory.
- **Tasks reference projects by id, not by name** — a name FK would need
  `ON UPDATE CASCADE` to survive renames, and that cascade fires only when
  `PRAGMA foreign_keys = ON` — per-connection and OFF by default in the
  `sqlite3` shell and most GUI tools — so a rename done outside the app would
  silently orphan every task. The `tasks_v` view keeps raw rows readable.
- **Theme has no CHECK** — valid theme names belong to the UI framework and
  change across its versions; the TUI validates on load and falls back to the
  default for stale names.
