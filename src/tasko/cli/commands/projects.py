from rich.markup import escape
from rich.table import Table

from tasko.cli import utils


def run(*, as_json: utils.JsonFlag = False, core: utils.InjectedCore) -> None:
    """List projects with task counts; JSON also identifies the default project.

    Parameters
    ----------
    as_json
        Print JSON instead of a table.
    core
        Injected by the launcher.

    """
    counts = core.project_task_counts()
    projects = core.list_projects()
    if as_json:
        default_project_id = core.app_state().default_project_id
        utils.print_json(
            [
                {
                    "name": project.name,
                    "open": counts.get(project.id, (0, 0))[0],
                    "total": counts.get(project.id, (0, 0))[1],
                    "is_default": project.id == default_project_id,
                }
                for project in projects
            ]
        )
        return
    table = Table("Project", "Open", "Total")
    for project in projects:
        open_count, total = counts.get(project.id, (0, 0))
        table.add_row(escape(project.name), str(open_count), str(total))
    utils.console.print(table)
