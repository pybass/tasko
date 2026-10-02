from tasko.cli import utils


def run(*, core: utils.InjectedCore) -> None:
    """Open the TUI."""
    # Imported here, not at module top: Textual costs ~90 ms, and every other command would pay it.
    from tasko.tui.app import TaskoApp  # noqa: PLC0415

    TaskoApp(core).run()
