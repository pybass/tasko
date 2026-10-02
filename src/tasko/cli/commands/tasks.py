from dataclasses import asdict
from typing import Annotated

from cyclopts import Parameter
from rich.markup import escape
from rich.table import Table

from tasko.cli import utils


def run(
    *,
    project: utils.ProjectName = None,
    include_done: Annotated[bool, Parameter(name="--all", negative="")] = False,
    as_json: utils.JsonFlag = False,
    core: utils.InjectedCore,
) -> None:
    """List open tasks: doing first, then by priority, then recently updated.

    Parameters
    ----------
    project
        Show only this project's tasks.
    include_done
        Include done tasks.
    as_json
        Print JSON instead of a table.
    core
        Injected by the launcher.

    """
    tasks = core.list_tasks(
        project_id=utils.project_id(core, project) if project is not None else None, include_done=include_done
    )
    if as_json:
        utils.print_json([asdict(task) for task in tasks])
        return
    if not tasks:
        utils.console.print("No tasks.")
        return
    table = Table("ID", "Project", "Status", "Priority", "Title")
    for task in tasks:
        table.add_row(str(task.id), escape(task.project_name), task.status, task.priority, escape(task.title))
    utils.console.print(table)
