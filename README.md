# tasko

A personal task manager: a fast Textual TUI over local SQLite.

## Usage

`tasko` launches the TUI — the only interface, where all task and project
management lives.

Data is a single SQLite file under `$XDG_DATA_HOME/tasko` (default
`~/.local/share/tasko`); override the directory with `--data-dir`.

## Design

- [docs/architecture.md](docs/architecture.md) — layering (`core/` + `tui/`),
  the TUI-only UI strategy, tool choices.
- [docs/data-model.md](docs/data-model.md) — entities, the full SQL schema,
  and the reasoning behind it.
- [docs/non-goals.md](docs/non-goals.md) — features deliberately not built,
  and why.

## License

[MIT](LICENSE)
