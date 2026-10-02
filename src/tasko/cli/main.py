"""CLI client: the TUI by default, plus task commands for scripts and agents."""

import os
import sys
from pathlib import Path
from typing import Annotated

from cyclopts import App, Parameter

from tasko.cli.commands import add, edit, projects, show, skill, status, tasks, tui
from tasko.core.core import Core
from tasko.core.errors import AppError

app = App(name="tasko", help="Personal task manager. Without a command, opens the TUI.")
app["--help"].show = False  # both flags keep working; they are just noise in the command list
app["--version"].show = False
app.default(tui.run)
# Explicit sort_key on every command fixes the help order (cyclopts sorts alphabetically without it).
app.command(tasks.run, name="list", sort_key=1)
app.command(show.run, name="show", sort_key=2)
app.command(add.run, name="add", sort_key=3)
app.command(edit.run, name="edit", sort_key=4)
app.command(status.run, name="status", sort_key=5)
app.command(projects.run, name="projects", sort_key=6)
app.command(skill.app)
skill.app.sort_key = 7  # sub-apps cannot take sort_key at registration time


@app.meta.default
def launcher(
    *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
    data_dir: Path | None = None,
) -> None:
    """Run the selected command, opening (and closing) the Core only when it asks for one.

    Parameters
    ----------
    tokens
        Raw CLI tokens, forwarded to the selected command.
    data_dir
        Data directory (default: XDG data dir).

    """
    command, bound, ignored = app.parse_args(tokens)
    if "core" not in ignored:  # --help, --version and the skill commands run without a database
        command(*bound.args, **bound.kwargs)
        return
    core = Core(_resolve_db_path(data_dir))
    try:
        command(*bound.args, **bound.kwargs, core=core)
    finally:
        core.close()


def main() -> None:
    """Console-script entry point: map AppError to a clean one-line exit."""
    try:
        app.meta()
    except AppError as e:
        sys.exit(f"error: {e}")


def _resolve_db_path(data_dir: Path | None) -> Path:
    """Database file path; without an explicit directory the XDG data dir is used."""
    if data_dir is None:
        data_dir = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "tasko"
    return data_dir / "tasko.db"
