from tasko.cli import utils
from tasko.core.models import Status


def run(task_id: int, status: Status, *, as_json: utils.JsonFlag = False, core: utils.InjectedCore) -> None:
    """Set a task's status and print the result.

    Parameters
    ----------
    task_id
        Task id.
    status
        New status.
    as_json
        Print JSON instead of text.
    core
        Injected by the launcher.

    """
    core.set_status(task_id, status)
    utils.print_task(core.get_task(task_id), as_json=as_json)
