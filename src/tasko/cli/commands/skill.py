import sys
from importlib.resources import files
from pathlib import Path
from typing import Annotated

from cyclopts import App, Parameter

from tasko.cli import utils
from tasko.core.errors import AppError

app = App(name="skill", help="The agent skill that teaches Claude Code and Codex to use tasko.")


@app.command
def show() -> None:
    """Print the skill text."""
    sys.stdout.write(_skill_text())


@app.command
def install(
    *,
    claude: Annotated[bool, Parameter(negative="")] = False,
    codex: Annotated[bool, Parameter(negative="")] = False,
    skills_dir: Annotated[Path | None, Parameter(name="--dir")] = None,
) -> None:
    """Write the skill into agent skill directories, replacing an existing copy.

    Parameters
    ----------
    claude
        Install for Claude Code (~/.claude/skills).
    codex
        Install for Codex (~/.agents/skills).
    skills_dir
        Install into this skills directory; the skill lands in DIR/tasko/SKILL.md.

    """
    targets = []
    if claude:
        targets.append(Path.home() / ".claude" / "skills")
    if codex:
        targets.append(Path.home() / ".agents" / "skills")
    if skills_dir is not None:
        targets.append(skills_dir)
    if not targets:
        raise AppError("Nothing to install: pass --claude, --codex or --dir.")
    paths = [target / "tasko" / "SKILL.md" for target in targets]
    for path in paths:
        # A symlinked skill directory points at someone's working copy; writing through it would overwrite that file.
        if path.parent.is_symlink():
            raise AppError(f"{path.parent} is a symlink; remove it or install with --dir.")
    text = _skill_text()
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        utils.console.print(f"Installed {path}", markup=False)


def _skill_text() -> str:
    """The skill shipped inside this package, so it always matches the installed commands."""
    return (files("tasko") / "SKILL.md").read_text(encoding="utf-8")
