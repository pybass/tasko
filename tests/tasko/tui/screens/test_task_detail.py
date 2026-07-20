"""TaskDetailScreen: per-field editing and deletion, driven headless via Pilot."""

import pytest

from tasko.core.errors import AppError
from tasko.core.models import Priority, Status
from tasko.tui.app import TaskoApp
from tasko.tui.screens.task_detail import TaskDetailScreen
from tasko.tui.screens.task_list import TaskListScreen


async def open_task(pilot):
    """Open the task under the cursor from the task list."""
    await pilot.press("enter")
    await pilot.pause()
    assert isinstance(pilot.app.screen, TaskDetailScreen)


class TestEditing:
    """Per-field edit dialogs."""

    async def test_title(self, core):
        """Pressing e edits the title, pre-filled with the current one (end deselects it)."""
        task = core.add_task("x")
        async with TaskoApp(core).run_test() as pilot:
            await open_task(pilot)
            await pilot.press("e")
            await pilot.pause()
            await pilot.press("end", "2", "enter")
            await pilot.pause()
            assert core.get_task(task.id).title == "x2"

    async def test_body(self, core):
        """Pressing b edits the body; Ctrl+S saves."""
        task = core.add_task("x")
        async with TaskoApp(core).run_test() as pilot:
            await open_task(pilot)
            await pilot.press("b")
            await pilot.pause()
            await pilot.press(*"note", "ctrl+s")
            await pilot.pause()
            assert core.get_task(task.id).body == "note"

    async def test_status_toggles(self, core):
        """Pressing d/s toggles done/doing with the same semantics as on the task list."""
        task = core.add_task("x")
        async with TaskoApp(core).run_test() as pilot:
            await open_task(pilot)
            await pilot.press("s")
            await pilot.pause()
            assert core.get_task(task.id).status is Status.DOING
            await pilot.press("d")
            await pilot.pause()
            assert core.get_task(task.id).status is Status.DONE
            await pilot.press("d")
            await pilot.pause()
            assert core.get_task(task.id).status is Status.TODO

    async def test_priority(self, core):
        """Pressing p picks a priority from the list (medium → high)."""
        task = core.add_task("x")
        async with TaskoApp(core).run_test() as pilot:
            await open_task(pilot)
            await pilot.press("p")
            await pilot.pause()
            await pilot.press("down", "enter")
            await pilot.pause()
            assert core.get_task(task.id).priority is Priority.HIGH

    async def test_project(self, core):
        """Pressing P moves the task to another project."""
        work = core.create_project("work")
        task = core.add_task("x")
        async with TaskoApp(core).run_test() as pilot:
            await open_task(pilot)
            await pilot.press("P")
            await pilot.pause()
            await pilot.press(*"work", "enter")
            await pilot.pause()
            assert core.get_task(task.id).project_id == work.id


class TestDelete:
    """Deleting the task from its screen."""

    async def test_cancel_keeps_task(self, core):
        """Answering n keeps the task and stays on the screen."""
        task = core.add_task("x")
        async with TaskoApp(core).run_test() as pilot:
            await open_task(pilot)
            await pilot.press("x")
            await pilot.pause()
            await pilot.press("n")
            await pilot.pause()
            assert isinstance(pilot.app.screen, TaskDetailScreen)
            assert core.get_task(task.id).title == "x"

    async def test_confirm_deletes(self, core):
        """Answering y deletes the task and returns to the task list."""
        task = core.add_task("x")
        async with TaskoApp(core).run_test() as pilot:
            await open_task(pilot)
            await pilot.press("x")
            await pilot.pause()
            await pilot.press("y")
            await pilot.pause()
            assert isinstance(pilot.app.screen, TaskListScreen)
            with pytest.raises(AppError, match="not found"):
                core.get_task(task.id)
