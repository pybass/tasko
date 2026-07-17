"""Shared TUI widgets."""

from typing import TYPE_CHECKING

from rich.text import Text
from textual.containers import Horizontal
from textual.widgets import Label

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.visual import VisualType


class StatusBar(Horizontal):
    """One-line bottom bar: the screen's context on the left, the help key hint on the right.

    Replaces both the stock Header (context) and Footer (key hints): the full key list
    lives behind the global help key, so the bar stays a single quiet line.
    """

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        padding: 0 1;
        background: $panel;
    }
    StatusBar > #context {
        width: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        """Render the context slot and the help hint."""
        yield Label(id="context")
        yield Label(Text.assemble(("?", "bold"), (" help", "dim")))

    def set_context(self, context: VisualType) -> None:
        """Put the screen's context (filter, counts, ...) on the left side of the bar."""
        self.query_one("#context", Label).update(context)
