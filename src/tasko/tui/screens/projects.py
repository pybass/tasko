"""Projects screen: a table of projects with management actions."""

from collections.abc import Callable
from typing import ClassVar, Final

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.screen import Screen
from textual.widgets import DataTable

from tasko.core.core import Core
from tasko.core.errors import AppError
from tasko.tui.keys import with_ru_layout
from tasko.tui.screens.dialogs import ConfirmDialog, InputDialog
from tasko.tui.widgets import StatusBar

_DEFAULT_CELL: Final = Text("default", style="green")  # marks the default project; space is not scarce here


class ProjectsScreen(Screen[None]):
    """Project management — rarely visited, reached from the task list with P."""

    BINDINGS: ClassVar[list[BindingType]] = with_ru_layout(
        [
            ("j", "cursor_down", "Down"),
            ("k", "cursor_up", "Up"),
            ("a", "add", "Add"),
            ("e", "rename", "Rename"),
            ("x", "delete", "Delete"),
            ("m", "make_default", "Make default"),
            ("escape", "app.pop_screen", "Back"),
        ]
    )

    # What ?/i shows: the user-facing key reference for this screen, in reading order.
    HELP_KEYS: ClassVar[list[tuple[str, str]]] = [
        ("↑ ↓ j k", "move the cursor"),
        ("a", "create a project"),
        ("e", "rename the project under the cursor"),
        ("x", "delete the project and all its tasks"),
        ("m", "make it the default for quick capture"),
        ("esc", "back to the task list"),
        ("? i", "this help"),
    ]

    def __init__(self, core: Core) -> None:
        """Wire the screen to the core."""
        super().__init__()
        self._core = core  # core operations

    def compose(self) -> ComposeResult:
        """Render the project table and the status bar."""
        yield DataTable()
        yield StatusBar()

    def on_mount(self) -> None:
        """Configure and fill the table."""
        table = self.query_one(DataTable)
        table.cursor_type = "row"  # actions apply to the row under the cursor
        table.add_columns("ID", "Name", "Default", "Tasks")
        self.reload()

    def reload(self) -> None:
        """Refill the table from the database, keeping the cursor on the same project when possible."""
        table = self.query_one(DataTable)
        previous_row = table.cursor_row
        previous_id = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value if table.row_count else None
        table.clear()
        counts = self._core.project_task_counts()
        default_id = self._core.app_state().default_project_id
        projects = self._core.list_projects()
        self.query_one(StatusBar).set_context(Text.assemble("projects", (f" · {len(projects)}", "dim")))
        ids = []
        for project in projects:
            ids.append(str(project.id))
            open_, total = counts.get(project.id, (0, 0))
            table.add_row(
                str(project.id),
                project.name,
                _DEFAULT_CELL if project.id == default_id else "",
                f"{open_}/{total}",  # open = todo + doing
                key=str(project.id),
            )
        if table.row_count:
            # Follow the project by id (rows reorder on rename); if it is gone, clamp the old position.
            row = ids.index(previous_id) if previous_id in ids else min(previous_row, table.row_count - 1)
            table.move_cursor(row=row)

    def _cursor_project_id(self) -> int | None:
        """Return the id of the project under the cursor, or None on an empty table.

        The id comes from the row key, never from cell content — cells are display
        and their order is free to change.
        """
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return None
        key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
        return int(key) if key is not None else None

    def _apply(self, operation: Callable[[], object]) -> None:
        """Run a core operation; refresh the table on success, toast the message on AppError."""
        try:
            operation()
        except AppError as e:
            self.notify(str(e), severity="error")
        else:
            self.reload()

    def action_cursor_down(self) -> None:
        """Move the cursor down — the vim-trained alias for the down arrow."""
        self.query_one(DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move the cursor up — the vim-trained alias for the up arrow."""
        self.query_one(DataTable).action_cursor_up()

    def action_add(self) -> None:
        """Prompt for a name and create a project."""

        def on_result(name: str | None) -> None:
            if name:
                self._apply(lambda: self._core.create_project(name))

        self.app.push_screen(InputDialog("New project name:"), on_result)

    def action_rename(self) -> None:
        """Prompt for a new name for the project under the cursor."""
        project_id = self._cursor_project_id()
        if project_id is None:
            return
        name = self._core.get_project(project_id).name

        def on_result(new_name: str | None) -> None:
            if new_name:
                self._apply(lambda: self._core.rename_project(project_id, new_name))

        self.app.push_screen(InputDialog("Rename project:", value=name), on_result)

    def action_delete(self) -> None:
        """Confirm and delete the project under the cursor together with its tasks."""
        project_id = self._cursor_project_id()
        if project_id is None:
            return
        name = self._core.get_project(project_id).name

        def on_result(confirmed: bool | None) -> None:
            if confirmed:
                self._apply(lambda: self._core.delete_project(project_id))

        self.app.push_screen(ConfirmDialog(f"Delete project '{name}' and all its tasks?"), on_result)

    def action_make_default(self) -> None:
        """Make the project under the cursor the default one."""
        project_id = self._cursor_project_id()
        if project_id is None:
            return
        self._apply(lambda: self._core.set_default_project(project_id))
