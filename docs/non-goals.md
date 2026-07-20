# Non-Goals

Features deliberately not built. The common reason: no real need has shown
up — tasko serves personal use, and a speculative feature costs maintenance
forever. Any entry here can be revisited when an actual need appears.

- **Due dates, reminders, scheduling.** A task has status, priority, and
  lifecycle timestamps; "do this by Friday" is not modeled. Current usage
  does not need it, and the column, sorting rules, and UI it would require
  are not worth carrying unused.

- **Scripting and automation integration.** No machine-readable output, no CLI
  commands, no API. Not a single script or agent uses tasko today; an
  integration surface would be maintained for nobody.

- **A `TASKO_DATA_DIR` env var.** `--data-dir` is the only override. A second
  way to point at the database lets a stale `export` silently open the wrong
  one. `XDG_DATA_HOME` is still honored.
