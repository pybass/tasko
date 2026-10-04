"""Main screen: the task table."""

from dataclasses import replace
from typing import ClassVar, Final

from rich.cells import cell_len
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Static

from tasko.core.core import Core
from tasko.core.errors import AppError
from tasko.core.models import Priority, Status, Task
from tasko.tui.keys import with_ru_layout
from tasko.tui.screens.dialogs import ConfirmDialog, InputDialog, SelectDialog
from tasko.tui.screens.projects import ProjectsScreen
from tasko.tui.screens.task_detail import TaskDetailScreen
from tasko.tui.widgets import StatusBar

# One-character, color-coded cells: the status, priority and body columns must not waste width.
_STATUS_CELLS: Final = {
    Status.TODO: Text("·", style="dim"),
    Status.DOING: Text("»", style="yellow"),
    Status.DONE: Text("✓", style="green"),
}
_PRIORITY_CELLS: Final = {
    Priority.HIGH: Text("↑", style="red"),
    Priority.MEDIUM: Text(""),  # the default level is visual silence
    Priority.LOW: Text("↓", style="dim"),
}
_BODY_CELL: Final = Text("≡", style="dim")  # marks that a task has a body; the text itself is shown elsewhere


def _title_cell(title: str, status: Status) -> Text:
    """Render a title cell: done tasks are struck through, and a title wider than its column ends in an ellipsis."""
    return Text(title, style="strike" if status is Status.DONE else "", overflow="ellipsis")


class TaskListScreen(Screen[None]):
    """Task list — the screen the app lives on."""

    BINDINGS: ClassVar[list[BindingType]] = with_ru_layout(
        [
            ("j", "cursor_down", "Down"),
            ("k", "cursor_up", "Up"),
            ("a", "add", "Add"),
            ("A", "add_with_project", "Add to project"),
            ("d", "toggle_done", "Done"),
            ("s", "toggle_doing", "Doing"),
            ("plus,equals_sign", "priority_up", "Priority up"),  # = raises too: + is shifted on most layouts
            ("minus", "priority_down", "Priority down"),
            ("x", "delete", "Delete"),
            ("D", "toggle_show_done", "Show done"),
            ("v", "toggle_preview", "Preview"),
            ("J", "preview_down", "Preview down"),
            ("K", "preview_up", "Preview up"),
            ("f", "focus_project", "Focus"),
            ("p", "select_project", "Project"),
            ("r", "refresh", "Refresh"),
            ("P", "projects", "Projects"),
            ("q", "app.quit", "Quit"),
        ]
    )

    # What ?/i shows: the user-facing key reference for this screen, in reading order.
    HELP_KEYS: ClassVar[list[tuple[str, str]]] = [
        ("↑ ↓ j k", "move the cursor"),
        ("enter", "open the task under the cursor"),
        ("a", "add a task into the cursor row's project"),
        ("A", "add a task, choosing the project first"),
        ("d", "mark done / back to todo"),
        ("s", "mark doing / back to todo"),
        ("+ -", "raise / lower the priority"),
        ("x", "delete the task"),
        ("D", "show or hide done tasks"),
        ("v", "show or hide the task preview"),
        ("J K", "scroll the preview"),
        ("f", "focus the cursor task's project / back to all"),
        ("p", "filter by project"),
        ("r", "refresh the list"),
        ("P", "manage projects"),
        ("q", "quit"),
        ("? i", "this help"),
    ]

    DEFAULT_CSS = """
    TaskListScreen #main.-beside {
        layout: horizontal;
    }
    TaskListScreen #preview {
        height: 35%;
        min-height: 6;
        padding: 0 2;
        border-top: solid $foreground 20%;
    }
    TaskListScreen #main.-beside #preview {
        height: 100%;
        padding: 1 2;  /* the title lines up with the first task row, below the table header */
        border-top: none;
        border-left: solid $foreground 20%;
    }
    TaskListScreen #preview-title {
        text-style: bold;
        margin-bottom: 1;
    }
    TaskListScreen #preview-body {
        color: $text-muted;
    }
    """

    def __init__(self, core: Core) -> None:
        """Wire the screen to the core."""
        super().__init__()
        self._core = core  # core operations
        self._show_done = False  # session-only toggle; done tasks are hidden by default
        self._show_preview = core.app_state().show_preview
        # The tasks on display by id, in list order: the preview and redraws read them instead of the database.
        self._tasks: dict[int, Task] = {}
        self._preview_task_id: int | None = None  # the task in the preview; a change resets the pane's scroll

    def compose(self) -> ComposeResult:
        """Render the task table, the preview pane and the status bar."""
        with Container(id="main"):
            yield DataTable()
            # Not focusable: the keyboard stays on the table, so the cursor keys keep browsing tasks.
            with VerticalScroll(id="preview", can_focus=False):
                yield Static(id="preview-title")
                yield Static(id="preview-body")
        yield StatusBar()

    def on_mount(self) -> None:
        """Configure and fill the table."""
        table = self.query_one(DataTable)
        table.cursor_type = "row"  # navigate whole rows; row actions will hang off the cursor row
        self.reload()

    def on_screen_resume(self) -> None:
        """Re-read the database when coming back from another screen (projects may have changed)."""
        self.reload()

    def on_resize(self) -> None:
        """Refit the list and the preview pane to the new terminal size."""
        if self._show_preview:
            self._redraw()

    def on_data_table_row_highlighted(self) -> None:
        """Keep the preview on the task under the cursor."""
        self._update_preview()

    def reload(self) -> None:
        """Re-read the tasks from the database and redraw the screen."""
        state = self._core.app_state()
        tasks = self._core.list_tasks(project_id=state.selected_project_id, include_done=self._show_done)
        self._tasks = {task.id: task for task in tasks}
        # The status bar shows the context: the project filter, plus task counts under it.
        # The filter project's name cannot come from the task rows — it may have zero tasks.
        if state.selected_project_id is not None:
            title = self._core.get_project(state.selected_project_id).name
        else:
            title = "all projects"
        open_count = sum(1 for task in tasks if task.status is not Status.DONE)
        counts = f" · {open_count} open · {len(tasks) - open_count} done" if self._show_done else f" · {open_count} open"
        self.query_one(StatusBar).set_context(Text.assemble(title, (counts, "dim")))
        self._redraw()

    def _redraw(self) -> None:
        """Lay out the preview pane and refill the table from the loaded tasks, keeping the cursor on the same task."""
        table = self.query_one(DataTable)
        previous_row = table.cursor_row
        previous_id = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value if table.row_count else None
        tasks = self._tasks.values()
        # The P column earns its width only when some visible task deviates from the default
        # priority. DataTable cannot hide a column in place, so columns are rebuilt every redraw.
        show_priority = any(task.priority is not Priority.MEDIUM for task in tasks)
        table.clear(columns=True)
        # Explicit widths sized to the content being added: auto-width is recomputed in a
        # deferred idle message, and a repaint racing ahead of it caches cells at label-only
        # widths (DataTable's cell render cache ignores width), leaving rows misaligned.
        id_width = max([1, *(len(str(task.id)) for task in tasks)])
        project_width = max([len("Project"), *(cell_len(task.project_name) for task in tasks)])
        title_width = max([len("Title"), *(cell_len(task.title) for task in tasks)])
        # The pane sits beside the list only on a wide terminal; otherwise it goes below and the list keeps its full width.
        width = self.app.size.width
        beside = self._show_preview and width >= 120
        pane_width = None
        if beside:
            # What the list needs besides the title: the other columns, one cell of padding on
            # each side of every column, and the two-cell vertical scrollbar.
            fixed_width = id_width + project_width + (17 if show_priority else 14)
            # The pane takes the room the list leaves: at most 80 columns, a readable line, and
            # at least 50, taken from the title column, where long titles are cut.
            pane_width = max(50, min(80, width - fixed_width - title_width))
            title_width = max(len("Title"), min(title_width, width - pane_width - fixed_width))
        preview = self.query_one("#preview")
        preview.display = self._show_preview
        preview.styles.width = pane_width
        self.query_one("#main").set_class(beside, "-beside")
        # One-letter labels for the status/priority glyph columns; the body marker column explains itself.
        table.add_column(Text("#", justify="right"), width=id_width)
        self._status_column = table.add_column("S", width=1)  # column keys for the in-place updates in _toggle_*
        self._priority_column = table.add_column("P", width=1) if show_priority else None  # None while hidden
        table.add_column("Project", width=project_width)
        self._title_column = table.add_column("Title", width=title_width)
        table.add_column("", width=1)
        ids = []
        for task in tasks:
            ids.append(str(task.id))
            # Ink hierarchy: the title is the content and stays bright; id and project are context and dim.
            table.add_row(
                Text(str(task.id), style="dim", justify="right"),
                _STATUS_CELLS[task.status],
                *([_PRIORITY_CELLS[task.priority]] if show_priority else []),
                Text(task.project_name, style="dim"),
                _title_cell(task.title, task.status),
                _BODY_CELL if task.body else "",
                key=str(task.id),
            )
        if table.row_count:
            # Follow the task by id; if it is gone, clamp the old position.
            row = ids.index(previous_id) if previous_id in ids else min(previous_row, table.row_count - 1)
            table.move_cursor(row=row)
        self._update_preview()

    def _update_preview(self) -> None:
        """Show the task under the cursor in the preview pane."""
        if not self._show_preview:
            return
        task_id = self._cursor_task_id()
        title = self.query_one("#preview-title", Static)
        body = self.query_one("#preview-body", Static)
        if task_id is None:
            title.update()
            body.update()
        else:
            task = self._tasks[task_id]
            # Text, not str: Static would parse square brackets in a str as markup.
            title.update(Text(task.title))
            body.update(Text(task.body) if task.body else Text("(no body)", style="dim"))
        if task_id != self._preview_task_id:
            self._preview_task_id = task_id
            self.query_one("#preview").scroll_home(animate=False)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Enter on a row opens the task screen."""
        if event.row_key.value is not None:
            self.app.push_screen(TaskDetailScreen(self._core, int(event.row_key.value)))

    def action_add(self) -> None:
        """Prompt for a title and create a task in the project named in the prompt.

        The target is the project of the row under the cursor — the context the user is
        looking at (it matters under the "all projects" filter); on an empty table it
        falls back to the selected, then the default project. Wrong target? Escape, move
        the cursor to a row of the right project, or change the project on the task later.
        """
        project_id = self._add_target_project_id()
        name = self._core.get_project(project_id).name

        def on_result(title: str | None) -> None:
            if not title:
                return
            try:
                self._core.add_task(title, project_id=project_id)
            except AppError as e:
                self.notify(str(e), severity="error")
            else:
                self.reload()

        self.app.push_screen(InputDialog(f'New task in "{name}":'), on_result)

    def action_add_with_project(self) -> None:
        """Pick the target project from the full list, then prompt for a title.

        The escape hatch for 'a': used when no visible row carries the wanted project.
        """
        options: list[tuple[str, str | Text]] = [(str(p.id), p.name) for p in self._core.list_projects()]
        # Preselect the project plain 'a' would target, so Enter-Enter behaves like 'a'.
        current = str(self._add_target_project_id())

        def on_project(choice: str | None) -> None:
            if choice is None:
                return
            project_id = int(choice)
            name = self._core.get_project(project_id).name

            def on_title(title: str | None) -> None:
                if not title:
                    return
                try:
                    self._core.add_task(title, project_id=project_id)
                except AppError as e:
                    self.notify(str(e), severity="error")
                    return
                self.reload()
                # The task is invisible when a different project filter is active — confirm it landed.
                filter_id = self._core.app_state().selected_project_id
                if filter_id is not None and filter_id != project_id:
                    self.notify(f'Added to "{name}"')

            self.app.push_screen(InputDialog(f'New task in "{name}":'), on_title)

        self.app.push_screen(SelectDialog("Add task to project:", options, current), on_project)

    def _add_target_project_id(self) -> int:
        """Project a plain add targets: the cursor row's project, else the selected, else the default one."""
        task_id = self._cursor_task_id()
        if task_id is not None:
            return self._core.get_task(task_id).project_id
        state = self._core.app_state()
        return state.selected_project_id or state.default_project_id

    def _cursor_task_id(self) -> int | None:
        """Return the id of the task under the cursor, or None on an empty table.

        The id comes from the row key, never from cell content — cells are styled
        display and their order is free to change.
        """
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return None
        key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
        return int(key) if key is not None else None

    def _toggle_status(self, target: Status) -> None:
        """Flip the cursor task into the target status (or back to todo), updating its row in place.

        Deliberately no reload: the row stays where it is, so an accidental press is
        visible and undone with the same key. The task re-sorts or disappears on the
        next natural reload.
        """
        task_id = self._cursor_task_id()
        if task_id is None:
            return
        try:
            task = self._core.get_task(task_id)
            status = Status.TODO if task.status is target else target
            self._core.set_status(task_id, status)
        except AppError as e:
            self.notify(str(e), severity="error")
            return
        self._tasks[task_id] = replace(task, status=status)  # a redraw reads the loaded copy, not the database
        table = self.query_one(DataTable)
        table.update_cell(str(task_id), self._status_column, _STATUS_CELLS[status])
        table.update_cell(str(task_id), self._title_column, _title_cell(task.title, status))

    def _shift_priority(self, step: int) -> None:
        """Move the cursor task one step along low → medium → high, updating its row in place.

        Same philosophy as _toggle_status: no reload, the change is visible under the
        cursor and the opposite key undoes it; the row re-sorts on the next reload. The
        exception is a hidden P column (everything was medium): only a reload can bring
        it back, and the cursor still follows the task by id.
        """
        task_id = self._cursor_task_id()
        if task_id is None:
            return
        try:
            task = self._core.get_task(task_id)
            scale = list(Priority)  # declared in scale order: low, medium, high
            index = scale.index(task.priority) + step
            if not 0 <= index < len(scale):
                return  # already at the end of the scale
            priority = scale[index]
            self._core.set_priority(task_id, priority)
        except AppError as e:
            self.notify(str(e), severity="error")
            return
        self._tasks[task_id] = replace(task, priority=priority)  # a redraw reads the loaded copy, not the database
        column = self._priority_column
        if column is None:
            self.reload()
        else:
            self.query_one(DataTable).update_cell(str(task_id), column, _PRIORITY_CELLS[priority])

    def action_toggle_done(self) -> None:
        """Toggle done for the task under the cursor: not-done → done, done → todo."""
        self._toggle_status(Status.DONE)

    def action_toggle_doing(self) -> None:
        """Toggle doing for the task under the cursor: not-doing → doing (even from done), doing → todo."""
        self._toggle_status(Status.DOING)

    def action_delete(self) -> None:
        """Confirm and delete the task under the cursor — the same dialog as on the detail screen."""
        task_id = self._cursor_task_id()
        if task_id is None:
            return
        try:
            task = self._core.get_task(task_id)
        except AppError as e:
            self.notify(str(e), severity="error")
            return

        def on_result(confirmed: bool | None) -> None:
            if not confirmed:
                return
            try:
                self._core.delete_task(task_id)
            except AppError as e:
                self.notify(str(e), severity="error")
            else:
                self.reload()

        self.app.push_screen(ConfirmDialog(f"Delete task '{task.title}'?"), on_result)

    def action_cursor_down(self) -> None:
        """Move the cursor down — the vim-trained alias for the down arrow."""
        self.query_one(DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move the cursor up — the vim-trained alias for the up arrow."""
        self.query_one(DataTable).action_cursor_up()

    def action_priority_up(self) -> None:
        """Raise the cursor task's priority one step."""
        self._shift_priority(1)

    def action_priority_down(self) -> None:
        """Lower the cursor task's priority one step."""
        self._shift_priority(-1)

    def action_toggle_show_done(self) -> None:
        """Show or hide done tasks."""
        self._show_done = not self._show_done
        self.reload()

    def action_toggle_preview(self) -> None:
        """Show or hide the preview pane; the choice persists across runs."""
        self._show_preview = not self._show_preview
        self._core.set_show_preview(self._show_preview)
        self._redraw()

    def action_preview_down(self) -> None:
        """Scroll the preview half a page down."""
        preview = self.query_one("#preview")
        preview.scroll_relative(y=preview.size.height // 2, animate=False)

    def action_preview_up(self) -> None:
        """Scroll the preview half a page up."""
        preview = self.query_one("#preview")
        preview.scroll_relative(y=-(preview.size.height // 2), animate=False)

    def action_refresh(self) -> None:
        """Reload the list: apply pending re-sorts/hides from d/s and pick up changes from another instance."""
        self.reload()

    def action_focus_project(self) -> None:
        """Toggle the filter: all projects → the cursor task's project, any project → all.

        The quick alternative to the picker: when narrowed, every visible task belongs
        to the filter project, so the two directions never overlap on one key.
        """
        if self._core.app_state().selected_project_id is not None:
            self._core.set_selected_project(None)
        else:
            task_id = self._cursor_task_id()
            if task_id is None:
                return
            self._core.set_selected_project(self._core.get_task(task_id).project_id)
        self.reload()

    def action_select_project(self) -> None:
        """Choose the project filter: a single project or all of them."""
        selected_id = self._core.app_state().selected_project_id
        # The meta-option is styled apart so it reads as a mode, not a project.
        options: list[tuple[str, str | Text]] = [("all", Text("All projects", style="italic dim"))]
        options += [(str(p.id), p.name) for p in self._core.list_projects()]
        current = "all" if selected_id is None else str(selected_id)

        def on_result(choice: str | None) -> None:
            if choice is not None:
                self._core.set_selected_project(None if choice == "all" else int(choice))
                self.reload()

        self.app.push_screen(SelectDialog("Project:", options, current), on_result)

    def action_projects(self) -> None:
        """Open the projects screen."""
        self.app.push_screen(ProjectsScreen(self._core))
