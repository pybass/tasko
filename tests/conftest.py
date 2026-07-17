"""Shared fixtures for the whole test suite."""

import pytest

from tasko.core.core import Core


@pytest.fixture
def core(tmp_path):
    """Core over a fresh temporary database."""
    core = Core(tmp_path / "tasko.db")
    yield core
    core.close()
