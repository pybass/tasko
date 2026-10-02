from rich.markup import escape
from rich.table import Table

from tasko.cli import utils


def run(*, as_json: utils.JsonFlag = False, core: utils.InjectedCore) -> None:
    """List projects with their open and total task counts.

    Parameters
    ----------
    as_json
        Print JSON instead of a table.
    core
        Injected by the launcher.

    """
    counts = core.project_task_counts()
    rows = [(project.name, *counts.get(project.id, (0, 0))) for project in core.list_projects()]
    if as_json:
        utils.print_json([{"name": name, "open": open_count, "total": total} for name, open_count, total in rows])
        return
    table = Table("Project", "Open", "Total")
    for name, open_count, total in rows:
        table.add_row(escape(name), str(open_count), str(total))
    utils.console.print(table)
