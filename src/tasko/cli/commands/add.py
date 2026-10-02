from tasko.cli import utils
from tasko.core.models import Priority


def run(
    title: str,
    *,
    project: utils.ProjectName = None,
    body: str | None = None,
    priority: Priority = Priority.MEDIUM,
    as_json: utils.JsonFlag = False,
    core: utils.InjectedCore,
) -> None:
    """Create a task and print it.

    Parameters
    ----------
    title
        Short summary.
    project
        Target project (default: the default project).
    body
        Long description.
    priority
        Task priority.
    as_json
        Print JSON instead of text.
    core
        Injected by the launcher.

    """
    # The default project, not Core's "selected or default": the TUI filter must not steer a script.
    project_id = utils.project_id(core, project) if project is not None else core.app_state().default_project_id
    utils.print_task(core.add_task(title, project_id=project_id, body=body, priority=priority), as_json=as_json)
