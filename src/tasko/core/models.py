"""Domain models: projects, tasks, and their enums."""

import sqlite3
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Self


class Priority(StrEnum):
    """Task priority; values match the TEXT stored in SQLite."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class Project:
    """A project — the mandatory container every task belongs to."""

    id: int  # stable identity; the display name can change freely
    name: str  # unique, non-empty


@dataclass(frozen=True, slots=True)
class Task:
    """A single task, always scoped to a project."""

    id: int  # stable id, never reused (AUTOINCREMENT)
    project_id: int  # owning project
    project_name: str  # owning project's name, joined in by core queries
    title: str  # short summary, non-empty
    body: str | None  # optional long description; on a closed task its first lines say the outcome
    priority: Priority  # low / medium / high
    created_at: int  # unix seconds
    updated_at: int  # unix seconds; equals created_at until the first modification
    closed_at: int | None  # unix seconds; None while the task is open

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Self:
        """Build a Task from a database row, coercing the TEXT priority into its enum."""
        data: dict[str, Any] = dict(row)
        data["priority"] = Priority(data["priority"])
        return cls(**data)


@dataclass(frozen=True, slots=True)
class AppState:
    """Singleton application state (the app_state table)."""

    default_project_id: int  # quick-capture target when no project is selected
    selected_project_id: int | None  # persisted project filter; None = all projects
    theme: str  # persisted UI theme name (a Textual built-in theme)
    show_preview: bool  # persisted TUI toggle: the preview pane on the task list
