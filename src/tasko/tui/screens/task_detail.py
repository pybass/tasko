"""Task detail screen: full details of one task with per-field editing."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import ClassVar, Final

from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from tasko.core.core import Core
from tasko.core.errors import AppError
from tasko.core.models import Priority, Status, Task
from tasko.tui.keys import with_ru_layout
from tasko.tui.screens.dialogs import ConfirmDialog, InputDialog, SelectDialog, TextDialog
from tasko.tui.widgets import StatusBar

# Same glyphs and colors as the table on the main screen, spelled out with the word.
_STATUS_TEXT: Final = {
    Status.TODO: Text("· todo", style="dim"),
    Status.DOING: Text("» doing", style="yellow"),
    Status.DONE: Text("✓ done", style="green"),
}
_PRIORITY_TEXT: Final = {
    Priority.HIGH: Text("high", style="red"),
    Priority.MEDIUM: Text("medium"),
    Priority.LOW: Text("low", style="dim"),
}


def _format_ts(ts: int | None) -> str:
    """Render unix seconds in local time, or an em dash when absent."""
    if ts is None:
        return "—"
    return datetime.fromtimestamp(ts, tz=UTC).astimezone().strftime("%Y-%m-%d %H:%M")


class TaskDetailScreen(Screen[None]):
    """Details of one task — reached from the task table with Enter."""

    BINDINGS: ClassVar[list[BindingType]] = with_ru_layout(
        [
            ("e", "edit_title", "Title"),
            ("b", "edit_body", "Body"),
            ("d", "toggle_done", "Done"),
            ("s", "toggle_doing", "Doing"),
            ("p", "edit_priority", "Priority"),
            ("P", "edit_project", "Project"),
            ("x", "delete", "Delete"),
            ("escape", "app.pop_screen", "Back"),
        ]
    )

    # What ?/i shows: the user-facing key reference for this screen, in reading order.
    HELP_KEYS: ClassVar[list[tuple[str, str]]] = [
        ("e", "edit the title"),
        ("b", "edit the body"),
        ("d", "mark done / back to todo"),
        ("s", "mark doing / back to todo"),
        ("p", "change the priority"),
        ("P", "move to another project"),
        ("x", "delete the task"),
        ("esc", "back to the task list"),
        ("? i", "this help"),
    ]

    DEFAULT_CSS = """
    TaskDetailScreen VerticalScroll {
        padding: 1 2;
    }
    TaskDetailScreen #title {
        text-style: bold;
        margin-bottom: 1;
    }
    TaskDetailScreen #meta {
        margin-bottom: 1;
    }
    TaskDetailScreen #body {
        color: $text-muted;
    }
    """

    def __init__(self, core: Core, task_id: int) -> None:
        """Wire the screen to the core and the task to show."""
        super().__init__()
        self._core = core  # core operations
        self._task_id = task_id  # id of the task on display
        self._loaded_task: Task | None = None  # last loaded state; None until the first reload

    def compose(self) -> ComposeResult:
        """Render the scrollable details (title, metadata, body) and the status bar."""
        with VerticalScroll():
            yield Static(id="title")
            yield Static(id="meta")
            yield Static(id="body")
        yield StatusBar()

    def on_mount(self) -> None:
        """Fill the screen."""
        self.reload()

    def on_screen_resume(self) -> None:
        """Re-read the task when coming back from an edit dialog."""
        # A resume can arrive after the screen was already popped (dialog dismiss posts it
        # before action_delete's callback runs); reloading then would pop a second screen.
        if self.is_current:
            self.reload()

    def reload(self) -> None:
        """Refresh all fields from the database; leave the screen if the task is gone."""
        try:
            task = self._core.get_task(self._task_id)
        except AppError as e:
            self.notify(str(e), severity="error")
            self.app.pop_screen()
            return
        self._loaded_task = task
        self.query_one(StatusBar).set_context(Text.assemble(f"task #{task.id}", (f" · {task.project_name}", "dim")))

        self.query_one("#title", Static).update(Text(task.title))
        # Two column groups: live fields on the left (main-table order), dates on the right; all dim but the field values.
        meta = Table.grid(padding=(0, 2))
        meta.add_column(style="dim")
        meta.add_column()
        meta.add_column(style="dim")
        meta.add_column(style="dim")
        meta.add_row("Status", _STATUS_TEXT[task.status], "Created", _format_ts(task.created_at))
        meta.add_row("Priority", _PRIORITY_TEXT[task.priority], "Updated", _format_ts(task.updated_at))
        meta.add_row("Project", task.project_name, "Done", _format_ts(task.done_at))
        self.query_one("#meta", Static).update(meta)
        body = self.query_one("#body", Static)
        body.update(task.body or Text("(no body)", style="dim"))

    def _apply(self, operation: Callable[[], object]) -> None:
        """Run a core operation; refresh the screen on success, toast the message on AppError."""
        try:
            operation()
        except AppError as e:
            self.notify(str(e), severity="error")
        else:
            self.reload()

    def action_edit_title(self) -> None:
        """Prompt for a new title, pre-filled with the current one."""
        if self._loaded_task is None:
            return

        def on_result(title: str | None) -> None:
            if title:
                self._apply(lambda: self._core.set_title(self._task_id, title))

        self.app.push_screen(InputDialog("Task title:", value=self._loaded_task.title), on_result)

    def action_edit_body(self) -> None:
        """Edit the body in a multi-line dialog; saving empty text clears it."""
        if self._loaded_task is None:
            return

        def on_result(text: str | None) -> None:
            if text is not None:
                self._apply(lambda: self._core.set_body(self._task_id, text))

        self.app.push_screen(TextDialog("Task body:", self._loaded_task.body or ""), on_result)

    def action_toggle_done(self) -> None:
        """Toggle done, same as on the task list: not-done → done, done → todo."""
        if self._loaded_task is None:
            return
        status = Status.TODO if self._loaded_task.status is Status.DONE else Status.DONE
        self._apply(lambda: self._core.set_status(self._task_id, status))

    def action_toggle_doing(self) -> None:
        """Toggle doing, same as on the task list: not-doing → doing (even from done), doing → todo."""
        if self._loaded_task is None:
            return
        status = Status.TODO if self._loaded_task.status is Status.DOING else Status.DOING
        self._apply(lambda: self._core.set_status(self._task_id, status))

    def action_edit_priority(self) -> None:
        """Pick a new priority, starting on the current one."""
        if self._loaded_task is None:
            return

        def on_result(choice: str | None) -> None:
            if choice is not None:
                self._apply(lambda: self._core.set_priority(self._task_id, Priority(choice)))

        options = [(priority.value, priority.value) for priority in Priority]
        self.app.push_screen(SelectDialog("Priority:", options, self._loaded_task.priority.value, filterable=False), on_result)

    def action_delete(self) -> None:
        """Confirm and delete the task, then return to the task list."""
        if self._loaded_task is None:
            return

        def on_result(confirmed: bool | None) -> None:
            if not confirmed:
                return
            try:
                self._core.delete_task(self._task_id)
            except AppError as e:
                self.notify(str(e), severity="error")
            else:
                self.app.pop_screen()

        self.app.push_screen(ConfirmDialog(f"Delete task '{self._loaded_task.title}'?"), on_result)

    def action_edit_project(self) -> None:
        """Pick a new project, starting on the current one."""
        if self._loaded_task is None:
            return

        def on_result(choice: str | None) -> None:
            if choice is not None:
                self._apply(lambda: self._core.set_project(self._task_id, int(choice)))

        options = [(str(project.id), project.name) for project in self._core.list_projects()]
        self.app.push_screen(SelectDialog("Project:", options, str(self._loaded_task.project_id)), on_result)
