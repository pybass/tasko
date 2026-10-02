"""Shared CLI helpers: parameter annotations, the output console, and task printing."""

import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Annotated

from cyclopts import Parameter
from rich.console import Console
from rich.markup import escape

from tasko.core.core import Core
from tasko.core.errors import AppError
from tasko.core.models import Task

type InjectedCore = Annotated[Core, Parameter(parse=False)]  # a Core injected by the launcher, invisible to CLI parsing
type ProjectName = Annotated[str | None, Parameter(alias="-p")]
type JsonFlag = Annotated[bool, Parameter(name="--json", negative="")]

# The one console every command prints through. highlight=False (no auto-colored numbers) and
# soft_wrap=True (no hard wrapping in pipes) make console.print behave like print() until a style
# is asked for; emoji=False keeps ":name:" in task text literal.
console = Console(highlight=False, soft_wrap=True, emoji=False)


def project_id(core: Core, name: str) -> int:
    """Return the id of the project with this exact name; raises AppError when there is none."""
    for project in core.list_projects():
        if project.name == name:
            return project.id
    raise AppError(f"Project '{name}' not found.")


def print_json(data: object) -> None:
    """Write JSON to stdout, bypassing rich so the text is never restyled or wrapped."""
    sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def print_task(task: Task, *, as_json: bool) -> None:
    """Print one task in full: JSON, or a short header followed by the body."""
    if as_json:
        print_json(asdict(task))
        return
    console.print(f"#{task.id} \\[{escape(task.project_name)}] {escape(task.title)}")
    dates = f"created {_format_timestamp(task.created_at)}, updated {_format_timestamp(task.updated_at)}"
    console.print(f"{task.status}, {task.priority} priority, {dates}")
    if task.body:
        console.print()
        console.print(escape(task.body))


def _format_timestamp(ts: int) -> str:
    """Format unix seconds as local time, 'YYYY-MM-DD HH:MM'."""
    return datetime.fromtimestamp(ts, tz=UTC).astimezone().strftime("%Y-%m-%d %H:%M")
