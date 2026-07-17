# tasko

A personal task manager: a fast Textual TUI over local SQLite, with a minimal
CLI for quick capture.

## Usage

`tasko` with no arguments launches the TUI — the primary interface, where all
task and project management lives.

The CLI is deliberately minimal (see
[docs/architecture.md](docs/architecture.md) for why):

```sh
tasko add "fix nginx" -p infra   # quick capture from the shell
tasko list                       # a quick look without launching the TUI
```

Data is a single SQLite file under `$XDG_DATA_HOME/tasko` (default
`~/.local/share/tasko`); override the directory with `--data-dir` or the
`TASKO_DATA_DIR` env var.

## Design

- [docs/architecture.md](docs/architecture.md) — layering (`core/` + `cli/` +
  `tui/`), the TUI-first UI strategy, tool choices.
- [docs/data-model.md](docs/data-model.md) — entities, the full SQL schema,
  and the reasoning behind it.
- [docs/non-goals.md](docs/non-goals.md) — features deliberately not built,
  and why.

## License

[MIT](LICENSE)
