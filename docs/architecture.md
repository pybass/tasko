# Architecture

## Layers

`core/` is the whole application without any UI. `cli/` and `tui/` are thin
adapters on top of it. The dependency is strictly one-way: adapters import
core; core never imports an adapter. This keeps core testable without UI and
makes new adapters cheap.

Inside `core/`, the single `Core` class owns the SQLite connection,
migrations, queries, and the business rules around them — there is no
separate data-access layer.

## Layout

```
src/tasko/
├── core/
│   ├── core.py         # Core: SQLite connection + all operations and invariants
│   ├── migrations.py   # schema migrations, applied in order by Core
│   ├── models.py       # Task, Project, AppState, Status, Priority
│   └── errors.py       # AppError — message shown to the user by adapters
├── cli/
│   └── main.py         # entry point: no args → launch TUI; else add / list
└── tui/
    ├── app.py          # app shell: mounts the main screen, theme, focus reload
    ├── widgets.py      # shared widgets (StatusBar)
    └── screens/        # task_list, task_detail, projects, dialogs
```

## UI strategy: TUI-first, minimal CLI

The TUI is the product — ~90% of real usage. `tasko` with no arguments
launches it.

The CLI exists for two things, and its scope is capped accordingly:

1. **Quick capture** — `tasko add "fix nginx" -p infra` from the shell,
   no context switch.
2. **A quick look** — `tasko list` shows the open tasks without launching
   the TUI.

CLI commands: `add`, `list`. Nothing else. Completing tasks, editing,
project management and everything else live in the TUI only; a new CLI
command is added only when a real need shows up — the core operation will
already exist, so the cost is a thin adapter. Scripting and automation
integration is deliberately out of scope (see [non-goals.md](non-goals.md)).

## Tools

- **CLI: argparse** — two commands do not justify a framework dependency.
- **TUI: Textual** — mature, actively maintained, on public PyPI.
- **Models: frozen, slotted dataclasses** — enums are `StrEnum` subclasses,
  so their values match the TEXT stored in SQLite. The database is the
  validator (STRICT tables + CHECKs); user input is validated in core with
  explicit errors.
