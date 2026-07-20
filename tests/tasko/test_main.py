"""Entry point: data-dir resolution."""

from pathlib import Path

from tasko.main import _resolve_db_path


class TestResolveDbPath:
    """Explicit directory → XDG default; the file name is fixed."""

    def test_explicit_dir(self, tmp_path):
        """An explicit directory wins over the default."""
        assert _resolve_db_path(tmp_path) == tmp_path / "tasko.db"

    def test_xdg_data_home(self, tmp_path, monkeypatch):
        """XDG_DATA_HOME provides the default parent directory."""
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
        assert _resolve_db_path(None) == tmp_path / "xdg" / "tasko" / "tasko.db"

    def test_home_fallback(self, monkeypatch):
        """Without XDG_DATA_HOME the default under the home directory is used."""
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        assert _resolve_db_path(None) == Path.home() / ".local" / "share" / "tasko" / "tasko.db"
