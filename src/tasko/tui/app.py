"""Textual application: a thin shell that mounts the main screen."""

from typing import TYPE_CHECKING, ClassVar

from textual.app import App

from tasko.tui.screens.dialogs import HelpDialog
from tasko.tui.screens.projects import ProjectsScreen
from tasko.tui.screens.task_detail import TaskDetailScreen
from tasko.tui.screens.task_list import TaskListScreen

if TYPE_CHECKING:
    from textual.binding import BindingType

    from tasko.core.core import Core


class TaskoApp(App[None]):
    """Interactive TUI for managing tasks."""

    TITLE = "tasko"  # terminal window/tab title

    BINDINGS: ClassVar[list[BindingType]] = [("question_mark,i", "help", "Help")]

    # One canvas: the screens share the table's background so content sits on a single surface.
    # Deliberately not a bare `Screen` selector — that would also repaint the modal dialogs
    # and kill their dimmed overlay.
    CSS = """
    TaskListScreen, TaskDetailScreen, ProjectsScreen {
        background: $surface;
    }
    DataTable {
        height: 1fr;
    }
    DataTable > .datatable--header {
        background: transparent;
        text-style: none;
        color: $text-muted;
    }
    """

    def __init__(self, core: Core) -> None:
        """Wire the app to the shared core."""
        super().__init__()
        self._core = core  # application core, built by main() and owned by it

    def action_help(self) -> None:
        """Show the current screen's keys; screens opt in by defining a HELP_KEYS attribute."""
        rows = getattr(self.screen, "HELP_KEYS", None)
        if rows:
            self.push_screen(HelpDialog(rows))

    def on_mount(self) -> None:
        """Restore the persisted theme and mount the main screen."""
        theme = self._core.app_state().theme
        if theme in self.available_themes:  # a stale name (theme gone from Textual) keeps the default
            self.theme = theme
        self.push_screen(TaskListScreen(self._core))

    def watch_theme(self, theme: str) -> None:
        """Persist every theme change (made via the ctrl+p command palette) across runs."""
        self._core.set_theme(theme)

    def on_app_focus(self) -> None:
        """Reload the visible screen when the terminal regains focus.

        The database can change under a running instance — a second tasko in another
        terminal — so alt-tabbing back shows a fresh list rather than a stale one.
        Skipped while a dialog is on top — reloading under a modal could
        fight the interaction in progress (r covers that case), and TaskDetailScreen.reload
        pops the top screen when its task is gone, which must never hit a dialog.
        """
        screen = self.screen
        if isinstance(screen, TaskListScreen | TaskDetailScreen | ProjectsScreen):
            screen.reload()
