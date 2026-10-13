# Non-Goals

Features deliberately not built. The common reason: no real need has shown
up — tasko serves personal use, and a speculative feature costs maintenance
forever. Any entry here can be revisited when an actual need appears.

- **Due dates, reminders, scheduling.** A task has priority and lifecycle
  timestamps; "do this by Friday" is not modeled. Current usage does not
  need it, and the column, sorting rules, and UI it would require are not
  worth carrying unused.

- **Tags.** A tag the application acts on is a state in disguise; one it
  ignores has no place in a one-line table whose only flexible column is
  the title. The title verb says what kind of task it is, the project says
  who does it, and lists are too short to filter.

- **Statuses beyond open and closed.** `doing` existed for three months with
  its own key and went unused: focus comes from the project filter and a
  high priority. `idea` and `blocked` are a low priority plus a first line
  in the body. `done` vs `dropped` cannot express a task half done and half
  dropped; the body can. See the state rule in
  [data-model.md](data-model.md).

- **Comments.** One person and their agents would be writing a thread with
  themselves. The outcome goes in front of the body when a task is closed;
  a later note is a dated line in the body.

- **Deleting tasks and managing projects from the CLI.** The CLI serves
  scripts and AI agents; destructive and structural changes stay in the TUI,
  where a person makes them.

- **A `TASKO_DATA_DIR` env var.** `--data-dir` is the only override. A second
  way to point at the database lets a stale `export` silently open the wrong
  one. `XDG_DATA_HOME` is still honored.
