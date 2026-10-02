from tasko.cli import utils
from tasko.core.errors import AppError
from tasko.core.models import Priority


def run(
    task_id: int,
    *,
    title: str | None = None,
    body: str | None = None,
    priority: Priority | None = None,
    project: utils.ProjectName = None,
    as_json: utils.JsonFlag = False,
    core: utils.InjectedCore,
) -> None:
    """Change a task's fields and print the result.

    Parameters
    ----------
    task_id
        Task id.
    title
        New title.
    body
        New long description; an empty string clears it.
    priority
        New priority.
    project
        Move the task to this project.
    as_json
        Print JSON instead of text.
    core
        Injected by the launcher.

    """
    if title is None and body is None and priority is None and project is None:
        raise AppError("Nothing to change: pass --title, --body, --priority or --project.")
    # The two steps that can reject input run first, so a bad value leaves the task untouched.
    project_id = utils.project_id(core, project) if project is not None else None
    if title is not None:
        core.set_title(task_id, title)
    if body is not None:
        core.set_body(task_id, body)
    if priority is not None:
        core.set_priority(task_id, priority)
    if project_id is not None:
        core.set_project(task_id, project_id)
    utils.print_task(core.get_task(task_id), as_json=as_json)
