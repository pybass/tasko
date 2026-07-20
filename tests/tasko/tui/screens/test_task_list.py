"""TaskListScreen: table rendering and keyboard actions, driven headless via Pilot."""

from textual.widgets import DataTable

from tasko.core.models import Priority, Status
from tasko.tui.app import TaskoApp
from tasko.tui.screens.projects import ProjectsScreen
from tasko.tui.screens.task_detail import TaskDetailScreen


def table(app):
    """Return the task table of the current screen."""
    return app.screen.query_one(DataTable)


class TestTable:
    """Rendering of the task list."""

    async def test_lists_open_tasks(self, core):
        """Done tasks are hidden by default."""
        open_task = core.add_task("alpha")
        done = core.add_task("beta")
        core.set_status(done.id, Status.DONE)
        async with TaskoApp(core).run_test() as pilot:
            await pilot.pause()
            assert table(pilot.app).row_count == 1
            assert str(table(pilot.app).get_row_at(0)[0]) == str(open_task.id)

    async def test_show_done_toggle(self, core):
        """Pressing D reveals and hides done tasks."""
        done = core.add_task("beta")
        core.set_status(done.id, Status.DONE)
        async with TaskoApp(core).run_test() as pilot:
            await pilot.pause()
            assert table(pilot.app).row_count == 0
            await pilot.press("D")
            await pilot.pause()
            assert table(pilot.app).row_count == 1
            await pilot.press("D")
            await pilot.pause()
            assert table(pilot.app).row_count == 0


class TestActions:
    """Keyboard actions on the task under the cursor."""

    async def test_add_via_dialog(self, core):
        """Pressing a prompts for a title and creates the task."""
        async with TaskoApp(core).run_test() as pilot:
            await pilot.press("a")
            await pilot.pause()
            await pilot.press(*"hello", "enter")
            await pilot.pause()
            assert [t.title for t in core.list_tasks()] == ["hello"]
            assert table(pilot.app).row_count == 1

    async def test_add_cancelled(self, core):
        """Escape closes the dialog without creating anything."""
        async with TaskoApp(core).run_test() as pilot:
            await pilot.press("a")
            await pilot.pause()
            await pilot.press(*"hello", "escape")
            await pilot.pause()
            assert core.list_tasks() == []

    async def test_toggle_done(self, core):
        """Pressing d completes the task; pressing again reopens it."""
        task = core.add_task("x")
        async with TaskoApp(core).run_test() as pilot:
            await pilot.press("d")
            await pilot.pause()
            assert core.get_task(task.id).status is Status.DONE
            await pilot.press("d")
            await pilot.pause()
            assert core.get_task(task.id).status is Status.TODO

    async def test_toggle_doing(self, core):
        """Pressing s starts the task; pressing again returns it to todo."""
        task = core.add_task("x")
        async with TaskoApp(core).run_test() as pilot:
            await pilot.press("s")
            await pilot.pause()
            assert core.get_task(task.id).status is Status.DOING
            await pilot.press("s")
            await pilot.pause()
            assert core.get_task(task.id).status is Status.TODO

    async def test_shift_priority(self, core):
        """+/- move the priority one step along low → medium → high, capped at the ends."""
        task = core.add_task("x")
        async with TaskoApp(core).run_test() as pilot:
            await pilot.press("plus")
            await pilot.pause()
            assert core.get_task(task.id).priority is Priority.HIGH
            await pilot.press("plus")  # already at the top: no-op
            await pilot.pause()
            assert core.get_task(task.id).priority is Priority.HIGH
            await pilot.press("minus", "minus")
            await pilot.pause()
            assert core.get_task(task.id).priority is Priority.LOW
            await pilot.press("equals_sign")  # = raises without shift
            await pilot.pause()
            assert core.get_task(task.id).priority is Priority.MEDIUM

    async def test_project_filter(self, core):
        """Pressing p picks the project filter; the table narrows to it."""
        work = core.create_project("work")
        core.add_task("inbox task")
        core.add_task("work task", project_id=work.id)
        async with TaskoApp(core).run_test() as pilot:
            await pilot.press("p")
            await pilot.pause()
            await pilot.press(*"work", "enter")
            await pilot.pause()
            assert core.app_state().selected_project_id == work.id
            assert table(pilot.app).row_count == 1

    async def test_open_task_screen(self, core):
        """Enter on a row opens the task screen."""
        core.add_task("x")
        async with TaskoApp(core).run_test() as pilot:
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(pilot.app.screen, TaskDetailScreen)

    async def test_open_projects_screen(self, core):
        """Pressing P opens the projects screen."""
        async with TaskoApp(core).run_test() as pilot:
            await pilot.press("P")
            await pilot.pause()
            assert isinstance(pilot.app.screen, ProjectsScreen)
