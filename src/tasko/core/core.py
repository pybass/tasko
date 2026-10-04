"""Application core: SQLite storage and business operations in one class."""

import sqlite3
import time
from pathlib import Path
from typing import Any

from tasko.core.errors import AppError
from tasko.core.migrations import MIGRATIONS
from tasko.core.models import AppState, Priority, Project, Status, Task


def _now() -> int:
    """Return the current unix time in whole seconds."""
    return int(time.time())


class Core:
    """The application without UI: owns the SQLite connection and every operation on it.

    Adapters (the TUI) call these methods and show AppError messages to the user.
    """

    def __init__(self, db_path: Path) -> None:
        """Open the database (creating the file and its directory if needed) and migrate it."""
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # autocommit: every write is a single self-committing statement; anything that ever
        # needs multi-statement atomicity must use explicit BEGIN/COMMIT (as _migrate does).
        self._conn = sqlite3.connect(db_path, autocommit=True)  # single shared connection
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA busy_timeout = 5000")
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def close(self) -> None:
        """Close the connection."""
        self._conn.close()

    def _migrate(self) -> None:
        """Apply pending migrations, tracked via PRAGMA user_version."""
        version = int(self._conn.execute("PRAGMA user_version").fetchone()[0])
        for number, script in enumerate(MIGRATIONS[version:], start=version + 1):
            # The script and the version bump commit together: a crash mid-migration rolls back
            # cleanly, so a migration is either fully applied and recorded, or not at all.
            self._conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {number};\nCOMMIT;")

    # --- Tasks ---

    def add_task(
        self, title: str, *, project_id: int | None = None, body: str | None = None, priority: Priority = Priority.MEDIUM
    ) -> Task:
        """Create a task and return it. Without a project id, it goes to the selected or default project."""
        title = title.strip()
        if not title:
            raise AppError("Task title cannot be empty.")
        if project_id is None:
            state = self.app_state()
            project_id = state.selected_project_id or state.default_project_id
        try:
            row = self._conn.execute(
                """
                INSERT INTO tasks (project_id, title, body, priority, created_at, updated_at)
                VALUES (:project_id, :title, :body, :priority, :now, :now)
                RETURNING id
                """,
                {"project_id": project_id, "title": title, "body": body, "priority": priority, "now": _now()},
            ).fetchone()
        except sqlite3.IntegrityError as e:  # foreign key: no such project
            raise AppError(f"Project #{project_id} not found.") from e
        return self.get_task(int(row["id"]))

    def get_task(self, task_id: int) -> Task:
        """Return a task by id; raises AppError when it does not exist."""
        row = self._conn.execute(
            "SELECT t.*, p.name AS project_name FROM tasks t JOIN projects p ON p.id = t.project_id WHERE t.id = ?",
            (task_id,),
        ).fetchone()
        if row is None:
            raise AppError(f"Task #{task_id} not found.")
        return Task.from_row(row)

    def list_tasks(self, *, project_id: int | None = None, include_done: bool = False) -> list[Task]:
        """Return tasks in working order, optionally filtered to one project; done tasks appear only with include_done.

        Working order: doing first, then by priority, then recently updated; done tasks
        sink to the bottom (recently finished first, since done_at == updated_at).
        """
        rows = self._conn.execute(
            """
            SELECT t.*, p.name AS project_name
            FROM tasks t JOIN projects p ON p.id = t.project_id
            WHERE (:project_id IS NULL OR t.project_id = :project_id)
              AND (:include_done OR t.status != 'done')
            ORDER BY t.status = 'done',
                     t.status = 'doing' DESC,
                     CASE t.priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                     t.updated_at DESC
            """,
            {"project_id": project_id, "include_done": include_done},
        ).fetchall()
        return [Task.from_row(row) for row in rows]

    def project_task_counts(self) -> dict[int, tuple[int, int]]:
        """Return {project_id: (open, total)} task counts; projects without tasks are absent."""
        rows = self._conn.execute(
            "SELECT project_id, sum(status != 'done') AS open, count(*) AS total FROM tasks GROUP BY project_id"
        ).fetchall()
        return {int(row["project_id"]): (int(row["open"]), int(row["total"])) for row in rows}

    def set_status(self, task_id: int, status: Status) -> None:
        """Move a task to the given status, maintaining done_at."""
        now = _now()  # one timestamp for both columns: on completion done_at == updated_at
        done_at = now if status is Status.DONE else None
        cur = self._conn.execute(
            "UPDATE tasks SET status = :status, done_at = :done_at, updated_at = :now WHERE id = :id",
            {"status": status, "done_at": done_at, "now": now, "id": task_id},
        )
        if cur.rowcount == 0:
            raise AppError(f"Task #{task_id} not found.")

    def set_title(self, task_id: int, title: str) -> None:
        """Rename a task; the new title must be non-empty."""
        title = title.strip()
        if not title:
            raise AppError("Task title cannot be empty.")
        cur = self._conn.execute(
            "UPDATE tasks SET title = :title, updated_at = :now WHERE id = :id",
            {"title": title, "now": _now(), "id": task_id},
        )
        if cur.rowcount == 0:
            raise AppError(f"Task #{task_id} not found.")

    def set_body(self, task_id: int, body: str | None) -> None:
        """Replace a task's body; empty or whitespace-only text clears it."""
        if body is not None:
            body = body.strip() or None
        cur = self._conn.execute(
            "UPDATE tasks SET body = :body, updated_at = :now WHERE id = :id",
            {"body": body, "now": _now(), "id": task_id},
        )
        if cur.rowcount == 0:
            raise AppError(f"Task #{task_id} not found.")

    def set_priority(self, task_id: int, priority: Priority) -> None:
        """Change a task's priority."""
        cur = self._conn.execute(
            "UPDATE tasks SET priority = :priority, updated_at = :now WHERE id = :id",
            {"priority": priority, "now": _now(), "id": task_id},
        )
        if cur.rowcount == 0:
            raise AppError(f"Task #{task_id} not found.")

    def set_project(self, task_id: int, project_id: int) -> None:
        """Move a task to another project."""
        try:
            cur = self._conn.execute(
                "UPDATE tasks SET project_id = :project_id, updated_at = :now WHERE id = :id",
                {"project_id": project_id, "now": _now(), "id": task_id},
            )
        except sqlite3.IntegrityError as e:  # foreign key: no such project
            raise AppError(f"Project #{project_id} not found.") from e
        if cur.rowcount == 0:
            raise AppError(f"Task #{task_id} not found.")

    def delete_task(self, task_id: int) -> None:
        """Delete a task permanently."""
        cur = self._conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        if cur.rowcount == 0:
            raise AppError(f"Task #{task_id} not found.")

    # --- Projects ---

    def list_projects(self) -> list[Project]:
        """Return all projects ordered by name."""
        rows = self._conn.execute("SELECT id, name FROM projects ORDER BY name").fetchall()
        return [Project(**dict(row)) for row in rows]

    def get_project(self, project_id: int) -> Project:
        """Return a project by id; raises AppError when it does not exist."""
        row = self._conn.execute("SELECT id, name FROM projects WHERE id = ?", (project_id,)).fetchone()
        if row is None:
            raise AppError(f"Project #{project_id} not found.")
        return Project(**dict(row))

    def create_project(self, name: str) -> Project:
        """Create a project with a unique non-empty name and return it."""
        name = name.strip()
        if not name:
            raise AppError("Project name cannot be empty.")
        try:
            row = self._conn.execute("INSERT INTO projects (name) VALUES (?) RETURNING id", (name,)).fetchone()
        except sqlite3.IntegrityError as e:
            raise AppError(f"Project '{name}' already exists.") from e
        return Project(id=row["id"], name=name)

    def rename_project(self, project_id: int, new_name: str) -> None:
        """Rename a project; the new name must be unique and non-empty."""
        new_name = new_name.strip()
        if not new_name:
            raise AppError("Project name cannot be empty.")
        try:
            cur = self._conn.execute("UPDATE projects SET name = ? WHERE id = ?", (new_name, project_id))
        except sqlite3.IntegrityError as e:
            raise AppError(f"Project '{new_name}' already exists.") from e
        if cur.rowcount == 0:
            raise AppError(f"Project #{project_id} not found.")

    def delete_project(self, project_id: int) -> None:
        """Delete a project together with its tasks (ON DELETE CASCADE); the default project cannot be deleted."""
        if project_id == self.app_state().default_project_id:
            raise AppError("Cannot delete the default project; make another project the default first.")
        cur = self._conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        if cur.rowcount == 0:
            raise AppError(f"Project #{project_id} not found.")

    # --- App state ---

    def app_state(self) -> AppState:
        """Return the singleton application state."""
        # Explicit columns, not *: the row also carries the singleton id, which AppState
        # does not model and the dataclass constructor would reject.
        row = self._conn.execute("SELECT default_project_id, selected_project_id, theme, show_preview FROM app_state").fetchone()
        if row is None:  # invariant broken — the database was edited outside the app; fail loudly
            raise RuntimeError("database invariant violated: app_state row missing")
        data: dict[str, Any] = dict(row)
        data["show_preview"] = bool(data["show_preview"])  # SQLite stores it as 0 or 1
        return AppState(**data)

    def set_selected_project(self, project_id: int | None) -> None:
        """Set the persisted project filter; None means all projects."""
        self._conn.execute("UPDATE app_state SET selected_project_id = ? WHERE id = 1", (project_id,))

    def set_theme(self, theme: str) -> None:
        """Persist the UI theme choice."""
        self._conn.execute("UPDATE app_state SET theme = ? WHERE id = 1", (theme,))

    def set_show_preview(self, show: bool) -> None:
        """Persist whether the task list shows the preview pane."""
        self._conn.execute("UPDATE app_state SET show_preview = ? WHERE id = 1", (show,))

    def set_default_project(self, project_id: int) -> None:
        """Make the given project the default target for quick capture."""
        try:
            self._conn.execute("UPDATE app_state SET default_project_id = ? WHERE id = 1", (project_id,))
        except sqlite3.IntegrityError as e:  # foreign key: no such project
            raise AppError(f"Project #{project_id} not found.") from e
