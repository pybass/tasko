# Data Model

## Entities

Two entity tables — `projects` and `tasks` — plus `app_state`, a singleton row
holding application-level state: the default project, the persisted project
filter, the UI theme, and the preview pane toggle.

The full SQL schema is in
[src/tasko/core/db/schema.py](../src/tasko/core/db/schema.py).

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
- **Foreign keys need `PRAGMA foreign_keys = ON`** — it is per-connection and
  OFF by default; the application enables it on every connection.
- **Tasks reference projects by id, not by name** — a name FK would need
  `ON UPDATE CASCADE` to survive renames, and that cascade fires only when
  `PRAGMA foreign_keys = ON` — per-connection and OFF by default in the
  `sqlite3` shell and most GUI tools — so a rename done outside the app would
  silently orphan every task. The `tasks_v` view keeps raw rows readable.
- **Theme has no CHECK** — valid theme names belong to the UI framework and
  change across its versions; the TUI validates on load and falls back to the
  default for stale names.
