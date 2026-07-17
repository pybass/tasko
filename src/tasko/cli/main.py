"""CLI adapter: quick capture and a quick look at the list. The TUI is the primary interface."""

# ruff: noqa: T201 -- printing to stdout is this module's purpose: every command's user-facing
# output goes through print(); the rule targets stray debug prints, which cannot exist here.

import argparse
import os
import sys
from importlib.metadata import version
from pathlib import Path

from tasko.core.core import Core
from tasko.core.errors import AppError
from tasko.core.models import Priority, Status

DATA_DIR_ENV_VAR = "TASKO_DATA_DIR"  # overrides the default data directory


def main() -> None:
    """Entry point: no subcommand launches the TUI; `add` and `list` serve capture and a quick look."""
    args = _build_parser().parse_args()
    core = Core(_resolve_db_path(args.data_dir))
    try:
        if args.command is None:
            # Lazy import: quick capture (`tasko add`) must not pay the TUI framework's import cost.
            from tasko.tui.app import TaskoApp  # noqa: PLC0415

            TaskoApp(core).run()
        elif args.command == "add":
            _cmd_add(core, args)
        else:
            _cmd_list(core, args)
    except AppError as e:
        sys.exit(f"error: {e}")
    finally:
        core.close()


def _resolve_db_path(data_dir: Path | None = None) -> Path:
    """Path to the SQLite database file, resolving the data directory as CLI arg → env var → XDG default."""
    if data_dir is None:
        env = os.environ.get(DATA_DIR_ENV_VAR)
        if env:
            data_dir = Path(env)
        else:
            xdg_data_home = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
            data_dir = xdg_data_home / "tasko"
    return data_dir / "tasko.db"


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with the `add` and `list` subcommands."""
    parser = argparse.ArgumentParser(prog="tasko", description="Personal task manager.")
    parser.add_argument("--version", action="version", version=version("tasko"))
    parser.add_argument("--data-dir", type=Path, help=f"data directory (env: {DATA_DIR_ENV_VAR}; default: XDG data dir)")
    subparsers = parser.add_subparsers(dest="command")

    add = subparsers.add_parser("add", help="add a task")
    add.add_argument("title", help="task title")
    add.add_argument("-p", "--project", help="project name (default: the default project)")
    add.add_argument("-b", "--body", help="longer description")
    add.add_argument("--priority", type=Priority, choices=list(Priority), default=Priority.MEDIUM, help="task priority")

    list_ = subparsers.add_parser("list", help="list tasks (open ones by default)")
    list_.add_argument("-p", "--project", help="filter by project name")
    list_.add_argument("-s", "--status", type=Status, choices=list(Status), help="filter by status")
    list_.add_argument("--all", action="store_true", help="include done tasks")
    return parser


def _cmd_add(core: Core, args: argparse.Namespace) -> None:
    """Create a task and confirm where it landed."""
    project_id = core.get_project_by_name(args.project).id if args.project is not None else None
    task = core.add_task(args.title, project_id=project_id, body=args.body, priority=args.priority)
    print(f"Task #{task.id} created in project '{task.project_name}'.")


def _cmd_list(core: Core, args: argparse.Namespace) -> None:
    """Print tasks as an aligned table."""
    project_id = core.get_project_by_name(args.project).id if args.project is not None else None
    tasks = core.list_tasks(project_id=project_id, status=args.status, include_done=args.all)
    if not tasks:
        print("No tasks.")
        return
    header = ("ID", "Project", "Status", "Priority", "Title")
    rows = [(str(t.id), t.project_name, t.status, t.priority, t.title) for t in tasks]
    widths = [max(len(row[i]) for row in (header, *rows)) for i in range(len(header))]
    for row in (header, *rows):
        print("  ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True)).rstrip())
