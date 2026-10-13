from tasko.cli import utils


def run(task_id: int, note: utils.BodyText = None, *, as_json: utils.JsonFlag = False, core: utils.InjectedCore) -> None:
    """Close a task and print it; the note is put in front of the body.

    Parameters
    ----------
    task_id
        Task id.
    note
        The outcome: what was done, what was not and why.
    as_json
        Print JSON instead of text.
    core
        Injected by the launcher.

    """
    core.close_task(task_id, note)
    utils.print_task(core.get_task(task_id), as_json=as_json)
