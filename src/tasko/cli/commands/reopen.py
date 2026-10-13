from tasko.cli import utils


def run(task_id: int, *, as_json: utils.JsonFlag = False, core: utils.InjectedCore) -> None:
    """Reopen a closed task and print it.

    Parameters
    ----------
    task_id
        Task id.
    as_json
        Print JSON instead of text.
    core
        Injected by the launcher.

    """
    core.reopen_task(task_id)
    utils.print_task(core.get_task(task_id), as_json=as_json)
