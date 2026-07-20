"""ProjectsScreen: project management actions, driven headless via Pilot."""

import pytest

from tasko.core.errors import AppError
from tasko.tui.app import TaskoApp
from tasko.tui.screens.projects import ProjectsScreen


async def open_projects(pilot):
    """Open the projects screen from the task list."""
    await pilot.press("P")
    await pilot.pause()
    assert isinstance(pilot.app.screen, ProjectsScreen)


class TestProjectsScreen:
    """Actions on the project under the cursor (rows are ordered by name)."""

    async def test_add(self, core):
        """Pressing a prompts for a name and creates the project."""
        async with TaskoApp(core).run_test() as pilot:
            await open_projects(pilot)
            await pilot.press("a")
            await pilot.pause()
            await pilot.press(*"work", "enter")
            await pilot.pause()
            assert [p.name for p in core.list_projects()] == ["inbox", "work"]

    async def test_rename(self, core):
        """Pressing e renames the project, pre-filled with the current name (end deselects it)."""
        async with TaskoApp(core).run_test() as pilot:
            await open_projects(pilot)
            await pilot.press("e")
            await pilot.pause()
            await pilot.press("end", "2", "enter")
            await pilot.pause()
            assert [p.name for p in core.list_projects()] == ["inbox2"]

    async def test_make_default(self, core):
        """Pressing m makes the project under the cursor the default."""
        work = core.create_project("work")
        async with TaskoApp(core).run_test() as pilot:
            await open_projects(pilot)
            await pilot.press("down", "m")
            await pilot.pause()
            assert core.app_state().default_project_id == work.id

    async def test_delete_cascades(self, core):
        """Pressing x deletes the confirmed project together with its tasks."""
        work = core.create_project("work")
        task = core.add_task("x", project_id=work.id)
        async with TaskoApp(core).run_test() as pilot:
            await open_projects(pilot)
            await pilot.press("down", "x")
            await pilot.pause()
            await pilot.press("y")
            await pilot.pause()
            assert [p.name for p in core.list_projects()] == ["inbox"]
            with pytest.raises(AppError, match="not found"):
                core.get_task(task.id)

    async def test_delete_default_refused(self, core):
        """Deleting the default project is refused; it stays in place."""
        async with TaskoApp(core).run_test() as pilot:
            await open_projects(pilot)
            await pilot.press("x")
            await pilot.pause()
            await pilot.press("y")
            await pilot.pause()
            assert [p.name for p in core.list_projects()] == ["inbox"]
