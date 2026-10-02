from tasko.cli import utils


def run(task_id: int, *, as_json: utils.JsonFlag = False, core: utils.InjectedCore) -> None:
    """Show one task with its body.

    Parameters
    ----------
    task_id
        Task id.
    as_json
        Print JSON instead of text.
    core
        Injected by the launcher.

    """
    utils.print_task(core.get_task(task_id), as_json=as_json)
