# Architecture

## Layers

`core/` is the whole application without any UI. `tui/` and `cli/` are thin
adapters on top of it. The dependency is strictly one-way: adapters import
core; core never imports an adapter. This keeps core testable without UI and
makes new adapters cheap.

Inside `core/`, the single `Core` class owns the SQLite connection, the
queries, and the business rules around them — there is no separate
data-access layer: a method is input validation, SQL, and the translation of
a database error, so a query layer would only pass calls through.

`core/db/` opens the database and brings its schema to the latest version;
it holds no queries. `schema.py` holds the full current schema; a new
database is made from it at the latest version. `migrations.py` brings older
databases up and is append-only: a released migration never changes, and a
mistake is fixed by a new migration. Every schema change adds a migration and
makes the same change in `schema.py`; a test checks that both give the same
database. A database that a newer tasko has migrated is refused.

## Layout

```
src/tasko/
├── SKILL.md            # agent skill, shipped in the wheel and installed by `tasko skill install`
├── core/
│   ├── core.py         # Core: SQLite connection + all operations and invariants
│   ├── db/
│   │   ├── db.py           # open_db: connection setup and the migration runner
│   │   ├── schema.py       # the full current schema; new databases are made from it
│   │   └── migrations.py   # append-only steps that bring older databases up
│   ├── models.py       # Task, Project, AppState, Status, Priority
│   └── errors.py       # AppError — message shown to the user by adapters
├── cli/
│   ├── main.py         # entry point: resolve data dir, open database, run a command
│   ├── utils.py        # shared parameter types, output console, task printing
│   └── commands/       # one module per command; tui.py opens the TUI
└── tui/
    ├── app.py          # app shell: mounts the main screen, theme, focus reload
    ├── widgets.py      # shared widgets (StatusBar)
    └── screens/        # task_list, task_detail, projects, dialogs
```

## UI strategy: TUI for people, CLI for agents

The TUI is where a person works: `tasko` with no command opens it, and all
task and project management lives there.

The CLI exists for scripts and AI agents. It covers reading, adding, and
updating tasks, and prints JSON with `--json`. It names projects, not ids,
so a caller can pass a repository name. Deleting tasks and managing projects
stay TUI-only: those are rare, destructive, and a person's call.

A CLI command only parses arguments, calls `Core`, and prints. Rules and
validation belong in `Core`, so both adapters behave the same.

The agent skill lives in the package, not in a separate repository: it
describes the CLI commands, so the two must change in one commit and ship in
one version. Change a command and `SKILL.md` together. The file sits in the
package root because a skill's name must match its folder name.

## Tools

- **CLI: cyclopts** — commands are typed functions; the `Status` and
  `Priority` enums become validated choices without extra code.
- **TUI: Textual** — mature, actively maintained, on public PyPI.
- **Models: frozen, slotted dataclasses** — enums are `StrEnum` subclasses,
  so their values match the TEXT stored in SQLite. The database is the
  validator (STRICT tables + CHECKs); user input is validated in core with
  explicit errors.
