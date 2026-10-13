from tasko.cli import utils
from tasko.core.errors import AppError
from tasko.core.models import Priority


def run(
    task_id: int,
    *,
    title: str | None = None,
    body: utils.BodyText = None,
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
    project_id = utils.project_id(core, project) if project is not None else None
    core.update_task(task_id, title=title, body=body, priority=priority, project_id=project_id)
    utils.print_task(core.get_task(task_id), as_json=as_json)
