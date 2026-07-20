"""Core business operations, exercised against a real temporary SQLite database."""

import time

import pytest

from tasko.core.errors import AppError
from tasko.core.models import Priority, Status


def ids(tasks):
    """Task ids in list order."""
    return [task.id for task in tasks]


class TestAddTask:
    """Task creation and quick-capture targeting."""

    def test_defaults(self, core):
        """A bare add lands in the default project as a medium-priority todo."""
        task = core.add_task("write tests")
        assert task.title == "write tests"
        assert task.project_id == core.app_state().default_project_id
        assert task.status is Status.TODO
        assert task.priority is Priority.MEDIUM
        assert task.body is None
        assert task.done_at is None
        assert task.created_at == task.updated_at
        assert abs(task.created_at - time.time()) < 5

    def test_explicit_project(self, core):
        """An explicit project id wins over the selected/default target."""
        work = core.create_project("work")
        assert core.add_task("x", project_id=work.id).project_id == work.id

    def test_targets_selected_project(self, core):
        """Without an explicit project, the task goes to the selected project."""
        work = core.create_project("work")
        core.set_selected_project(work.id)
        assert core.add_task("x").project_id == work.id

    def test_body_and_priority(self, core):
        """Optional body and priority are stored."""
        task = core.add_task("x", body="details", priority=Priority.HIGH)
        assert task.body == "details"
        assert task.priority is Priority.HIGH

    def test_strips_title(self, core):
        """Surrounding whitespace is trimmed."""
        assert core.add_task("  x  ").title == "x"

    @pytest.mark.parametrize("title", ["", "   ", "\n"])
    def test_empty_title(self, core, title):
        """Empty or whitespace-only titles are rejected."""
        with pytest.raises(AppError, match="title cannot be empty"):
            core.add_task(title)

    def test_unknown_project(self, core):
        """A dangling project id is rejected via the foreign key."""
        with pytest.raises(AppError, match="not found"):
            core.add_task("x", project_id=999)


class TestGetTask:
    """Single-task lookup."""

    def test_missing(self, core):
        """An unknown id raises AppError."""
        with pytest.raises(AppError, match="Task #999 not found"):
            core.get_task(999)


class TestListTasks:
    """Listing and its working order."""

    def test_working_order(self, core):
        """Doing first, then by priority, done tasks sink to the bottom."""
        high = core.add_task("high", priority=Priority.HIGH)
        low = core.add_task("low", priority=Priority.LOW)
        doing = core.add_task("doing", priority=Priority.LOW)
        core.set_status(doing.id, Status.DOING)
        done = core.add_task("done", priority=Priority.HIGH)
        core.set_status(done.id, Status.DONE)
        assert ids(core.list_tasks(include_done=True)) == [doing.id, high.id, low.id, done.id]
        assert ids(core.list_tasks()) == [doing.id, high.id, low.id]

    def test_filter_by_project(self, core):
        """Only the given project's tasks are returned."""
        work = core.create_project("work")
        core.add_task("inbox task")
        work_task = core.add_task("work task", project_id=work.id)
        assert ids(core.list_tasks(project_id=work.id)) == [work_task.id]

    def test_filter_by_status(self, core):
        """Only tasks with the given status are returned."""
        core.add_task("open")
        done = core.add_task("finished")
        core.set_status(done.id, Status.DONE)
        assert ids(core.list_tasks(status=Status.DONE)) == [done.id]

    def test_hides_done_by_default(self, core):
        """Done tasks appear only with include_done."""
        open_task = core.add_task("open")
        done = core.add_task("finished")
        core.set_status(done.id, Status.DONE)
        assert ids(core.list_tasks()) == [open_task.id]
        assert ids(core.list_tasks(include_done=True)) == [open_task.id, done.id]


class TestProjectTaskCounts:
    """Per-project (open, total) counters."""

    def test_counts(self, core):
        """Counts are grouped by project; projects without tasks are absent."""
        inbox = core.get_project(core.app_state().default_project_id)
        core.create_project("empty")
        core.add_task("open")
        done = core.add_task("finished")
        core.set_status(done.id, Status.DONE)
        assert core.project_task_counts() == {inbox.id: (1, 2)}


class TestSetStatus:
    """Status transitions and the done_at invariant."""

    def test_done_sets_done_at(self, core):
        """Completing a task stamps done_at together with updated_at."""
        task = core.add_task("x")
        core.set_status(task.id, Status.DONE)
        task = core.get_task(task.id)
        assert task.status is Status.DONE
        assert task.done_at == task.updated_at

    def test_reopen_clears_done_at(self, core):
        """Moving a done task back clears done_at."""
        task = core.add_task("x")
        core.set_status(task.id, Status.DONE)
        core.set_status(task.id, Status.TODO)
        task = core.get_task(task.id)
        assert task.status is Status.TODO
        assert task.done_at is None

    def test_missing(self, core):
        """An unknown id raises AppError."""
        with pytest.raises(AppError, match="not found"):
            core.set_status(999, Status.DONE)


class TestSetTitle:
    """Renaming a task."""

    def test_rename(self, core):
        """The new title is stored trimmed."""
        task = core.add_task("x")
        core.set_title(task.id, "  y  ")
        assert core.get_task(task.id).title == "y"

    @pytest.mark.parametrize("title", ["", "   "])
    def test_empty_title(self, core, title):
        """Empty titles are rejected."""
        task = core.add_task("x")
        with pytest.raises(AppError, match="title cannot be empty"):
            core.set_title(task.id, title)

    def test_missing(self, core):
        """An unknown id raises AppError."""
        with pytest.raises(AppError, match="not found"):
            core.set_title(999, "y")


class TestSetBody:
    """Replacing and clearing the body."""

    def test_set(self, core):
        """A non-empty body is stored."""
        task = core.add_task("x")
        core.set_body(task.id, "details")
        assert core.get_task(task.id).body == "details"

    @pytest.mark.parametrize("body", [None, "", "   "])
    def test_clear(self, core, body):
        """None, empty, or whitespace-only text clears the body."""
        task = core.add_task("x", body="details")
        core.set_body(task.id, body)
        assert core.get_task(task.id).body is None

    def test_missing(self, core):
        """An unknown id raises AppError."""
        with pytest.raises(AppError, match="not found"):
            core.set_body(999, "details")


class TestSetPriority:
    """Changing the priority."""

    def test_change(self, core):
        """The new priority is stored."""
        task = core.add_task("x")
        core.set_priority(task.id, Priority.HIGH)
        assert core.get_task(task.id).priority is Priority.HIGH

    def test_missing(self, core):
        """An unknown id raises AppError."""
        with pytest.raises(AppError, match="not found"):
            core.set_priority(999, Priority.LOW)


class TestSetProject:
    """Moving a task between projects."""

    def test_move(self, core):
        """The task ends up in the target project."""
        work = core.create_project("work")
        task = core.add_task("x")
        core.set_project(task.id, work.id)
        assert core.get_task(task.id).project_id == work.id

    def test_unknown_project(self, core):
        """A dangling project id is rejected via the foreign key."""
        task = core.add_task("x")
        with pytest.raises(AppError, match="Project #999 not found"):
            core.set_project(task.id, 999)

    def test_missing_task(self, core):
        """An unknown task id raises AppError."""
        inbox = core.get_project(core.app_state().default_project_id)
        with pytest.raises(AppError, match="Task #999 not found"):
            core.set_project(999, inbox.id)


class TestDeleteTask:
    """Deleting a single task."""

    def test_delete(self, core):
        """The task is gone afterwards."""
        task = core.add_task("x")
        core.delete_task(task.id)
        with pytest.raises(AppError, match="not found"):
            core.get_task(task.id)

    def test_missing(self, core):
        """An unknown id raises AppError."""
        with pytest.raises(AppError, match="not found"):
            core.delete_task(999)


class TestProjects:
    """Project CRUD."""

    def test_list_ordered_by_name(self, core):
        """Projects come back alphabetically."""
        core.create_project("zebra")
        core.create_project("alpha")
        assert [p.name for p in core.list_projects()] == ["alpha", "inbox", "zebra"]

    def test_create_strips_name(self, core):
        """Surrounding whitespace is trimmed."""
        assert core.create_project("  work  ").name == "work"

    def test_create_duplicate(self, core):
        """Names are unique."""
        core.create_project("work")
        with pytest.raises(AppError, match="already exists"):
            core.create_project("work")

    @pytest.mark.parametrize("name", ["", "   "])
    def test_create_empty_name(self, core, name):
        """Empty names are rejected."""
        with pytest.raises(AppError, match="name cannot be empty"):
            core.create_project(name)

    def test_rename(self, core):
        """The new name is stored."""
        work = core.create_project("work")
        core.rename_project(work.id, "job")
        assert core.get_project(work.id).name == "job"

    def test_rename_duplicate(self, core):
        """Renaming onto an existing name is rejected."""
        work = core.create_project("work")
        with pytest.raises(AppError, match="already exists"):
            core.rename_project(work.id, "inbox")

    def test_rename_missing(self, core):
        """An unknown id raises AppError."""
        with pytest.raises(AppError, match="not found"):
            core.rename_project(999, "x")


class TestDeleteProject:
    """Project deletion and its invariants."""

    def test_cascades_to_tasks(self, core):
        """Deleting a project deletes its tasks with it."""
        work = core.create_project("work")
        task = core.add_task("x", project_id=work.id)
        core.delete_project(work.id)
        with pytest.raises(AppError, match="not found"):
            core.get_task(task.id)
        with pytest.raises(AppError, match="not found"):
            core.get_project(work.id)

    def test_default_refused(self, core):
        """The default project cannot be deleted."""
        with pytest.raises(AppError, match="Cannot delete the default project"):
            core.delete_project(core.app_state().default_project_id)

    def test_resets_selected_filter(self, core):
        """Deleting the selected project resets the filter to all projects."""
        work = core.create_project("work")
        core.set_selected_project(work.id)
        core.delete_project(work.id)
        assert core.app_state().selected_project_id is None

    def test_missing(self, core):
        """An unknown id raises AppError."""
        with pytest.raises(AppError, match="not found"):
            core.delete_project(999)


class TestAppState:
    """The singleton application state."""

    def test_initial(self, core):
        """A fresh database defaults to the seed project with no filter."""
        state = core.app_state()
        assert core.get_project(state.default_project_id).name == "inbox"
        assert state.selected_project_id is None

    def test_set_selected(self, core):
        """The filter can be set and cleared."""
        work = core.create_project("work")
        core.set_selected_project(work.id)
        assert core.app_state().selected_project_id == work.id
        core.set_selected_project(None)
        assert core.app_state().selected_project_id is None

    def test_set_default(self, core):
        """Any project can be made the default."""
        work = core.create_project("work")
        core.set_default_project(work.id)
        assert core.app_state().default_project_id == work.id

    def test_set_default_unknown(self, core):
        """A dangling project id is rejected via the foreign key."""
        with pytest.raises(AppError, match="Project #999 not found"):
            core.set_default_project(999)
