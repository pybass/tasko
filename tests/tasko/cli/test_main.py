"""CLI adapter: add and list run in-process against a real database, plus data-dir resolution."""

import sys
from pathlib import Path

import pytest

from tasko.cli.main import _resolve_db_path, main
from tasko.core.models import Priority, Status


@pytest.fixture
def cli(tmp_path, monkeypatch, capsys):
    """Callable running the CLI against the temp data dir; returns captured stdout.

    Uses the same database file as the `core` fixture, so tests can seed and
    inspect the data directly.
    """

    def run(*args):
        monkeypatch.setattr(sys, "argv", ["tasko", "--data-dir", str(tmp_path), *args])
        main()
        return capsys.readouterr().out

    return run


class TestAdd:
    """The add command."""

    def test_add_to_default(self, cli):
        """A bare add lands in the default project and confirms it."""
        assert cli("add", "buy milk") == "Task #1 created in project 'inbox'.\n"

    def test_add_to_project(self, cli, core):
        """-p sends the task to the named project."""
        core.create_project("work")
        assert cli("add", "x", "-p", "work") == "Task #1 created in project 'work'.\n"
        assert core.get_task(1).project_id == core.get_project_by_name("work").id

    def test_priority_and_body(self, cli, core):
        """--priority and -b are stored."""
        cli("add", "x", "--priority", "high", "-b", "details")
        task = core.get_task(1)
        assert task.priority is Priority.HIGH
        assert task.body == "details"

    def test_unknown_project(self, cli):
        """An unknown project name exits with an error message."""
        with pytest.raises(SystemExit, match="Project 'nope' not found"):
            cli("add", "x", "-p", "nope")


class TestList:
    """The list command."""

    def test_empty(self, cli):
        """An empty database prints a placeholder."""
        assert cli("list") == "No tasks.\n"

    def test_table(self, cli):
        """The table starts with a header row and contains every task."""
        cli("add", "first")
        cli("add", "second")
        out = cli("list")
        assert out.splitlines()[0].split() == ["ID", "Project", "Status", "Priority", "Title"]
        assert "first" in out
        assert "second" in out

    def test_status_filter(self, cli, core):
        """-s narrows the listing to one status."""
        cli("add", "open")
        done = core.add_task("finished")
        core.set_status(done.id, Status.DONE)
        out = cli("list", "-s", "done")
        assert "finished" in out
        assert "open" not in out

    def test_project_filter(self, cli, core):
        """-p narrows the listing to one project."""
        core.create_project("work")
        cli("add", "inbox task")
        cli("add", "work task", "-p", "work")
        out = cli("list", "-p", "work")
        assert "work task" in out
        assert "inbox task" not in out


class TestResolveDbPath:
    """CLI arg → env var → XDG default resolution; the file name is fixed."""

    def test_explicit_dir(self, tmp_path):
        """An explicit directory wins over everything."""
        assert _resolve_db_path(tmp_path) == tmp_path / "tasko.db"

    def test_env_var(self, tmp_path, monkeypatch):
        """TASKO_DATA_DIR is used when no directory is given."""
        monkeypatch.setenv("TASKO_DATA_DIR", str(tmp_path / "custom"))
        assert _resolve_db_path() == tmp_path / "custom" / "tasko.db"

    def test_xdg_data_home(self, tmp_path, monkeypatch):
        """XDG_DATA_HOME provides the default parent directory."""
        monkeypatch.delenv("TASKO_DATA_DIR", raising=False)
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
        assert _resolve_db_path() == tmp_path / "xdg" / "tasko" / "tasko.db"

    def test_home_fallback(self, monkeypatch):
        """Without any overrides the XDG default under the home directory is used."""
        monkeypatch.delenv("TASKO_DATA_DIR", raising=False)
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        assert _resolve_db_path() == Path.home() / ".local" / "share" / "tasko" / "tasko.db"
