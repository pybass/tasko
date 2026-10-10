from tasko.cli import utils
lazy from tasko.tui.app import TaskoApp


def run(*, project: utils.ProjectName = None, core: utils.InjectedCore) -> None:
    """Open the TUI.

    Parameters
    ----------
    project
        Open with the filter set to this project.
    core
        Injected by the launcher.

    """
    if project is not None:
        core.set_selected_project(utils.project_id(core, project))
    TaskoApp(core).run()
