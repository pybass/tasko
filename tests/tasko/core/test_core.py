"""Core business operations, exercised against a real temporary SQLite database."""

import itertools
import time

import pytest

from tasko.core.errors import AppError
from tasko.core.models import Priority


def ids(tasks):
    """Task ids in list order."""
    return [task.id for task in tasks]


class TestAddTask:
    """Task creation and quick-capture targeting."""

    def test_defaults(self, core):
        """A bare add lands in the default project as an open medium-priority task."""
        task = core.add_task("write tests")
        assert task.title == "write tests"
        assert task.project_id == core.app_state().default_project_id
        assert task.priority is Priority.MEDIUM
        assert task.body is None
        assert task.closed_at is None
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

    def test_working_order(self, core, monkeypatch):
        """By priority, then most recently updated; closed tasks sink to the bottom, recently closed first."""
        clock = itertools.count(1_000_000)  # real time is whole seconds: every write here would share one timestamp
        monkeypatch.setattr("tasko.core.core._now", lambda: next(clock))
        low = core.add_task("low", priority=Priority.LOW)
        older = core.add_task("older")
        newer = core.add_task("newer")
        high = core.add_task("high", priority=Priority.HIGH)
        closed_first = core.add_task("closed first", priority=Priority.HIGH)
        closed_last = core.add_task("closed last")
        core.close_task(closed_first.id)
        core.close_task(closed_last.id)
        core.update_task(older.id, title="older, edited")  # now the most recently updated medium task
        expected = [high.id, older.id, newer.id, low.id, closed_last.id, closed_first.id]
        assert ids(core.list_tasks(include_closed=True)) == expected
        assert ids(core.list_tasks()) == expected[:4]

    def test_filter_by_project(self, core):
        """Only the given project's tasks are returned."""
        work = core.create_project("work")
        core.add_task("inbox task")
        work_task = core.add_task("work task", project_id=work.id)
        assert ids(core.list_tasks(project_id=work.id)) == [work_task.id]

    def test_hides_closed_by_default(self, core):
        """Closed tasks appear only with include_closed."""
        open_task = core.add_task("open")
        closed = core.add_task("finished")
        core.close_task(closed.id)
        assert ids(core.list_tasks()) == [open_task.id]
        assert ids(core.list_tasks(include_closed=True)) == [open_task.id, closed.id]


class TestProjectTaskCounts:
    """Per-project (open, total) counters."""

    def test_counts(self, core):
        """Counts are grouped by project; projects without tasks are absent."""
        inbox = core.get_project(core.app_state().default_project_id)
        core.create_project("empty")
        core.add_task("open")
        closed = core.add_task("finished")
        core.close_task(closed.id)
        assert core.project_task_counts() == {inbox.id: (1, 2)}


class TestCloseTask:
    """Closing: the timestamp and the note in front of the body."""

    def test_sets_closed_at(self, core):
        """Closing stamps closed_at together with updated_at and leaves the body alone."""
        task = core.add_task("x", body="details")
        core.close_task(task.id)
        task = core.get_task(task.id)
        assert task.closed_at == task.updated_at
        assert task.body == "details"

    def test_note_goes_first(self, core):
        """The note is put in front of the body, separated by a blank line."""
        task = core.add_task("x", body="details")
        core.close_task(task.id, "Done; left: the host check.")
        assert core.get_task(task.id).body == "Done; left: the host check.\n\ndetails"

    def test_note_without_body(self, core):
        """On an empty body the note becomes the body."""
        task = core.add_task("x")
        core.close_task(task.id, "  Rejected.  ")
        assert core.get_task(task.id).body == "Rejected."

    @pytest.mark.parametrize("note", ["", "   "])
    def test_blank_note(self, core, note):
        """A blank note is the same as none."""
        task = core.add_task("x", body="details")
        core.close_task(task.id, note)
        assert core.get_task(task.id).body == "details"

    def test_already_closed(self, core):
        """A second close is refused, so a stale caller cannot prepend a second note."""
        task = core.add_task("x")
        core.close_task(task.id)
        with pytest.raises(AppError, match="already closed"):
            core.close_task(task.id, "again")

    def test_missing(self, core):
        """An unknown id raises AppError."""
        with pytest.raises(AppError, match="not found"):
            core.close_task(999)


class TestReopenTask:
    """Reopening clears the timestamp and keeps the body."""

    def test_reopen(self, core):
        """closed_at is cleared; the body, note included, stays."""
        task = core.add_task("x")
        core.close_task(task.id, "Done.")
        core.reopen_task(task.id)
        task = core.get_task(task.id)
        assert task.closed_at is None
        assert task.body == "Done."

    def test_not_closed(self, core):
        """Reopening an open task is refused."""
        task = core.add_task("x")
        with pytest.raises(AppError, match="not closed"):
            core.reopen_task(task.id)

    def test_missing(self, core):
        """An unknown id raises AppError."""
        with pytest.raises(AppError, match="not found"):
            core.reopen_task(999)


class TestUpdateTask:
    """Changing one or several fields in one statement."""

    def test_all_fields(self, core):
        """Every given field is stored; the title is trimmed."""
        work = core.create_project("work")
        task = core.add_task("x")
        core.update_task(task.id, title="  y  ", body="details", priority=Priority.HIGH, project_id=work.id)
        updated = core.get_task(task.id)
        assert (updated.title, updated.body, updated.priority, updated.project_id) == ("y", "details", Priority.HIGH, work.id)

    def test_none_leaves_field_alone(self, core):
        """Fields not given keep their values."""
        task = core.add_task("x", body="details", priority=Priority.HIGH)
        core.update_task(task.id, title="y")
        updated = core.get_task(task.id)
        assert (updated.title, updated.body, updated.priority) == ("y", "details", Priority.HIGH)

    @pytest.mark.parametrize("body", ["", "   "])
    def test_clear_body(self, core, body):
        """Empty or whitespace-only text clears the body."""
        task = core.add_task("x", body="details")
        core.update_task(task.id, body=body)
        assert core.get_task(task.id).body is None

    @pytest.mark.parametrize("title", ["", "   "])
    def test_empty_title(self, core, title):
        """Empty titles are rejected."""
        task = core.add_task("x")
        with pytest.raises(AppError, match="title cannot be empty"):
            core.update_task(task.id, title=title)

    def test_nothing_to_change(self, core):
        """A call without fields is an error, not a silent touch."""
        task = core.add_task("x")
        with pytest.raises(AppError, match="Nothing to change"):
            core.update_task(task.id)

    def test_rejected_value_changes_nothing(self, core):
        """A dangling project id is rejected via the foreign key, and the other fields stay as they were."""
        task = core.add_task("x")
        with pytest.raises(AppError, match="Project #999 not found"):
            core.update_task(task.id, title="y", project_id=999)
        assert core.get_task(task.id).title == "x"

    def test_missing_task(self, core):
        """An unknown task id raises AppError."""
        with pytest.raises(AppError, match="Task #999 not found"):
            core.update_task(999, title="y")


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
