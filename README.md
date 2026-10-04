# tasko

A personal task manager: a fast Textual TUI over local SQLite.

## Usage

`tasko` launches the TUI, where all task and project management lives.
`tasko -p PROJECT` opens it with the filter set to that project.

Commands give scripts and AI agents access to the same tasks:

```
tasko list [-p PROJECT] [--all]      # open tasks; --all adds done ones
tasko show ID
tasko add TITLE [-p PROJECT] [--body TEXT] [--priority low|medium|high]
tasko edit ID [--title T] [--body TEXT] [--priority P] [-p PROJECT]
tasko status ID todo|doing|done
tasko projects
```

Every command takes `--json`. Projects are given by name; `add` without
`-p` uses the default project. `projects --json` includes `is_default` for
each project.

## Agent skill

tasko ships a skill that teaches Claude Code and Codex to read, add, and
update tasks through these commands:

```
tasko skill install --claude         # ~/.claude/skills/tasko
tasko skill install --codex          # ~/.agents/skills/tasko
tasko skill install --dir PATH       # PATH/tasko, e.g. a project's .claude/skills
tasko skill show                     # print the skill text
```

The flags combine. The skill describes the commands of the installed
version, so run `install` again after upgrading tasko.

Data is a single SQLite file under `$XDG_DATA_HOME/tasko` (default
`~/.local/share/tasko`); override the directory with `--data-dir`.

## Design

- [docs/architecture.md](docs/architecture.md) — layering (`core/` + adapters),
  the TUI and CLI roles, tool choices.
- [docs/data-model.md](docs/data-model.md) — entities, invariants, and the
  reasoning behind them.
- [docs/non-goals.md](docs/non-goals.md) — features deliberately not built,
  and why.

## License

[MIT](LICENSE)
