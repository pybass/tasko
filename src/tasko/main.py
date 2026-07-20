"""Entry point: resolve the data directory, open the database, run the TUI."""

import argparse
import os
import sys
from importlib.metadata import version
from pathlib import Path

from tasko.core.core import Core
from tasko.core.errors import AppError
from tasko.tui.app import TaskoApp


def main() -> None:
    """Launch the TUI against the resolved database."""
    parser = argparse.ArgumentParser(prog="tasko", description="Personal task manager.")
    parser.add_argument("--version", action="version", version=version("tasko"))
    parser.add_argument("--data-dir", type=Path, help="data directory (default: XDG data dir)")
    args = parser.parse_args()
    core = Core(_resolve_db_path(args.data_dir))
    try:
        TaskoApp(core).run()
    except AppError as e:
        sys.exit(f"error: {e}")
    finally:
        core.close()


def _resolve_db_path(data_dir: Path | None) -> Path:
    """Database file path; without an explicit directory the XDG data dir is used."""
    if data_dir is None:
        data_dir = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "tasko"
    return data_dir / "tasko.db"
