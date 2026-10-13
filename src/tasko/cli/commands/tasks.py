from dataclasses import asdict
from typing import Annotated

from cyclopts import Parameter
from rich.markup import escape
from rich.table import Table

from tasko.cli import utils


def run(
    *,
    project: utils.ProjectName = None,
    include_closed: Annotated[bool, Parameter(name="--all", negative="")] = False,
    as_json: utils.JsonFlag = False,
    core: utils.InjectedCore,
) -> None:
    """List open tasks: by priority, then recently updated.

    Parameters
    ----------
    project
        Show only this project's tasks.
    include_closed
        Include closed tasks, after the open ones.
    as_json
        Print JSON instead of a table.
    core
        Injected by the launcher.

    """
    tasks = core.list_tasks(
        project_id=utils.project_id(core, project) if project is not None else None, include_closed=include_closed
    )
    if as_json:
        utils.print_json([asdict(task) for task in tasks])
        return
    if not tasks:
        utils.console.print("No tasks.")
        return
    # The State column exists only when closed rows can appear; otherwise every row would say "open".
    table = Table("ID", "Project", *(["State"] if include_closed else []), "Priority", "Title")
    for task in tasks:
        state = ["open" if task.closed_at is None else "closed"] if include_closed else []
        table.add_row(str(task.id), escape(task.project_name), *state, task.priority, escape(task.title))
    utils.console.print(table)
