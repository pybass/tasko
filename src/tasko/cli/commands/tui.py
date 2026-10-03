from tasko.cli import utils


def run(*, project: utils.ProjectName = None, core: utils.InjectedCore) -> None:
    """Open the TUI.

    Parameters
    ----------
    project
        Open with the filter set to this project.
    core
        Injected by the launcher.

    """
    # Imported here, not at module top: Textual costs ~90 ms, and every other command would pay it.
    from tasko.tui.app import TaskoApp  # noqa: PLC0415

    if project is not None:
        core.set_selected_project(utils.project_id(core, project))
    TaskoApp(core).run()
