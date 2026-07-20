# Architecture

## Layers

`core/` is the whole application without any UI. `tui/` is a thin adapter on
top of it, and `main.py` only wires the two together. The dependency is
strictly one-way: adapters import core; core never imports an adapter. This
keeps core testable without UI and makes new adapters cheap — the TUI is the
only one today, but nothing about core assumes it.

Inside `core/`, the single `Core` class owns the SQLite connection,
migrations, queries, and the business rules around them — there is no
separate data-access layer.

## Layout

```
src/tasko/
├── main.py             # entry point: resolve data dir, open database, run TUI
├── core/
│   ├── core.py         # Core: SQLite connection + all operations and invariants
│   ├── migrations.py   # schema migrations, applied in order by Core
│   ├── models.py       # Task, Project, AppState, Status, Priority
│   └── errors.py       # AppError — message shown to the user by adapters
└── tui/
    ├── app.py          # app shell: mounts the main screen, theme, focus reload
    ├── widgets.py      # shared widgets (StatusBar)
    └── screens/        # task_list, task_detail, projects, dialogs
```

## UI strategy: TUI-only

The TUI is the product — it is all of real usage. `tasko` launches it; there
is nothing else to run.

`main.py` is not a command layer. It resolves the data directory, opens the
database, and hands the resulting `Core` to the TUI. Its whole surface is
`--data-dir` and `--version`.

A CLI command is added only when a real need shows up — the core operation
already exists, so the cost is a thin adapter. Scripting and automation
integration stays out of scope (see [non-goals.md](non-goals.md)).

## Tools

- **Arguments: argparse** — two flags do not justify a framework dependency.
- **TUI: Textual** — mature, actively maintained, on public PyPI.
- **Models: frozen, slotted dataclasses** — enums are `StrEnum` subclasses,
  so their values match the TEXT stored in SQLite. The database is the
  validator (STRICT tables + CHECKs); user input is validated in core with
  explicit errors.
