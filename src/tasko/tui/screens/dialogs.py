"""Reusable modal dialogs: one-line and multi-line text input, yes/no confirmation, option picking, and key help."""

from collections.abc import Sequence
from importlib.metadata import version
from typing import ClassVar, Final

from rich.style import Style
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.fuzzy import FuzzySearch
from textual.screen import ModalScreen
from textual.widgets import Input, Label, OptionList, Static, TextArea
from textual.widgets.option_list import Option

_MATCH_STYLE: Final = Style(bold=True, underline=True)  # characters of a label the fuzzy query matched


class Dialog[ResultT](ModalScreen[ResultT]):
    """Base modal dialog: a centered bordered panel over the dimmed screen; Escape cancels with None."""

    DEFAULT_CSS = """
    Dialog {
        align: center middle;
    }
    Dialog > Vertical {
        width: 60;
        height: auto;
        padding: 1 2;
        border: round $primary;
        background: $surface;
    }
    Dialog Input {
        margin: 1 0 0 0;
        background: $boost;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [("escape", "cancel", "Cancel")]

    def action_cancel(self) -> None:
        """Cancel the dialog without a result."""
        self.dismiss(None)


class InputDialog(Dialog[str | None]):
    """Prompt for one line of text; dismisses with the value, or None on cancel."""

    # Wider than the base panel: one-line values (task titles) routinely outgrow 60 cells.
    DEFAULT_CSS = """
    InputDialog > Vertical {
        width: 80%;
    }
    """

    def __init__(self, title: str, value: str = "") -> None:
        """Set the prompt title and the optional pre-filled value."""
        super().__init__()
        self._title = title  # prompt shown above the input
        self._value = value  # initial input content

    def compose(self) -> ComposeResult:
        """Render the prompt: label + input."""
        with Vertical():
            yield Label(self._title)
            yield Input(value=self._value, compact=True)

    def on_mount(self) -> None:
        """Focus the input so typing starts immediately."""
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter accepts the value."""
        self.dismiss(event.value)


class TextDialog(Dialog[str | None]):
    """Edit multi-line text; dismisses with the text on Ctrl+S, or None on cancel.

    Enter inserts a newline inside the TextArea, so saving lives on Ctrl+S.
    """

    # Nearly full-screen: this edits prose, not a one-liner.
    DEFAULT_CSS = """
    TextDialog > Vertical {
        width: 90%;
        height: 90%;
    }
    TextDialog TextArea {
        margin: 1 0;
        height: 1fr;
        background: $boost;
        border: none;
        padding: 0 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("ctrl+s", "save", "Save"),
        # priority: the TextArea itself binds ctrl+a to "cursor to line start"; the GUI
        # habit (select all) wins here, line start stays available on Home.
        Binding("ctrl+a", "select_all", "Select all", priority=True),
    ]

    def __init__(self, title: str, text: str = "") -> None:
        """Set the prompt title and the initial text."""
        super().__init__()
        self._title = title  # prompt shown above the editor
        self._text = text  # initial editor content

    def compose(self) -> ComposeResult:
        """Render the prompt: label + editor + key hint."""
        with Vertical():
            yield Label(self._title)
            yield TextArea(self._text)
            yield Label("[b]ctrl+s[/b] — save    [b]ctrl+a[/b] — select all    [b]esc[/b] — cancel")

    def on_mount(self) -> None:
        """Focus the editor so typing starts immediately."""
        self.query_one(TextArea).focus()

    def action_save(self) -> None:
        """Ctrl+S accepts the text."""
        self.dismiss(self.query_one(TextArea).text)

    def action_select_all(self) -> None:
        """Ctrl+A selects the whole text, e.g. to replace or delete a long body at once."""
        self.query_one(TextArea).select_all()


class ConfirmDialog(Dialog[bool]):
    """Ask a yes/no question; dismisses with True only on explicit confirmation."""

    # Only the accent differs from the base panel: warning border for a destructive question.
    DEFAULT_CSS = """
    ConfirmDialog > Vertical {
        border: round $warning;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("y", "confirm", "Yes"),
        ("n", "cancel", "No"),
    ]

    def __init__(self, question: str) -> None:
        """Set the question text."""
        super().__init__()
        self._question = question  # what the user is asked to confirm

    def compose(self) -> ComposeResult:
        """Render the question and the key hint."""
        with Vertical():
            yield Label(self._question)
            yield Label("[b]y[/b] — yes    [b]n[/b]/[b]esc[/b] — no")

    def action_confirm(self) -> None:
        """Confirm the action."""
        self.dismiss(True)


class HelpDialog(Dialog[None]):
    """Show the current screen's keys as a two-column list; Escape, ? or i closes it."""

    # The about line sits under the keys, quiet and centered.
    DEFAULT_CSS = """
    HelpDialog #about {
        margin-top: 1;
        width: 100%;
        text-align: center;
        color: $text-muted;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [("question_mark,i", "cancel", "Close")]

    def __init__(self, rows: list[tuple[str, str]]) -> None:
        """Set the (key, description) rows in display order."""
        super().__init__()
        self._rows = rows  # curated per screen; see the HELP_KEYS attribute on screens

    def compose(self) -> ComposeResult:
        """Render the title, the key table, and the app name with its version."""
        grid = Table.grid(padding=(0, 2))
        grid.add_column(justify="right", style="bold")
        grid.add_column()
        for key, description in self._rows:
            grid.add_row(key, description)
        with Vertical():
            yield Label("Keys")
            yield Static(grid, id="keys")
            yield Label(f"tasko v{version('tasko')}", id="about")


class SelectDialog(Dialog[str | None]):
    """Pick one option with arrows and Enter; dismisses with the option id, or None on cancel.

    With `filterable` (the default) a query input keeps the focus the whole time:
    printable keys narrow the list fuzzily, up/down move the highlight. Pass
    `filterable=False` for short fixed sets where a filter is only noise.
    """

    DEFAULT_CSS = """
    SelectDialog OptionList {
        margin-top: 1;
        height: auto;
        max-height: 20;
        border: none;
        padding: 0;
        background: transparent;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
        ("pageup", "page_up", "Page up"),
        ("pagedown", "page_down", "Page down"),
        # priority: Input binds home/end to text-cursor moves; with a short filter
        # query, jumping the list matters more. ctrl+a/ctrl+e still edit the query.
        Binding("home", "first", "First", priority=True),
        Binding("end", "last", "Last", priority=True),
    ]

    def __init__(
        self, title: str, options: Sequence[tuple[str, str | Text]], current: str | None = None, *, filterable: bool = True
    ) -> None:
        """Set the prompt title, the (id, label) options in display order, and the id the cursor starts on.

        A label may come pre-styled as a Text (e.g. a meta-option rendered apart from
        the real entries); its plain text drives the fuzzy filter.
        """
        super().__init__()
        self._title = title  # prompt shown above the list
        # (id, label) pairs; ids must be unique. Labels normalize to Text so styled and plain ones flow the same.
        self._options = [(option_id, label if isinstance(label, Text) else Text(label)) for option_id, label in options]
        self._current = current  # option id highlighted initially, None for the first one
        self._filterable = filterable  # False renders no query input; the list itself takes the focus

    def compose(self) -> ComposeResult:
        """Render the prompt: label + optional fuzzy query input + option list."""
        with Vertical():
            yield Label(self._title)
            if self._filterable:
                yield Input(placeholder="type to filter", compact=True)
            yield OptionList(*[Option(label, id=option_id) for option_id, label in self._options])

    def on_mount(self) -> None:
        """Focus the input (or the list itself) and start the list cursor on the current option."""
        option_list = self.query_one(OptionList)
        if self._filterable:
            self.query_one(Input).focus()
        else:
            option_list.focus()
        if self._current is not None:
            option_list.highlighted = option_list.get_option_index(self._current)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Refill the list with fuzzy matches, best first; an empty query shows everything."""
        query = event.value
        option_list = self.query_one(OptionList)
        options = self._options
        if query:
            fuzzy = FuzzySearch()
            # One match() call per option yields both the score and the matched offsets.
            # Ties keep the original order (sort is stable).
            matches = [(fuzzy.match(query, label.plain), option_id, label) for option_id, label in options]
            matches.sort(key=lambda m: -m[0][0])
            options = []
            for (score, offsets), option_id, label in matches:
                if score <= 0:
                    break  # sorted best-first: everything from here on is unmatched
                # Underline the matched characters on a copy — stylizing in place would pile up across refilters.
                prompt = label.copy()
                for offset in offsets:
                    prompt.stylize(_MATCH_STYLE, offset, offset + 1)
                options.append((option_id, prompt))
        option_list.clear_options()
        for option_id, label in options:
            option_list.add_option(Option(label, id=option_id))
        if option_list.option_count:
            option_list.highlighted = 0

    def on_input_submitted(self) -> None:
        """Enter accepts the highlighted option; with no matches it does nothing."""
        option_list = self.query_one(OptionList)
        if option_list.highlighted is not None:
            self.dismiss(option_list.get_option_at_index(option_list.highlighted).id)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Mouse click — or Enter on the focused list — accepts an option directly."""
        self.dismiss(event.option_id)

    def action_cursor_up(self) -> None:
        """Move the list highlight up without leaving the input."""
        self.query_one(OptionList).action_cursor_up()

    def action_cursor_down(self) -> None:
        """Move the list highlight down without leaving the input."""
        self.query_one(OptionList).action_cursor_down()

    def action_page_up(self) -> None:
        """Move the list highlight one page up without leaving the input."""
        # textual's OptionList.action_page_up lacks a return annotation; the call is safe
        self.query_one(OptionList).action_page_up()  # type: ignore[no-untyped-call]

    def action_page_down(self) -> None:
        """Move the list highlight one page down without leaving the input."""
        # textual's OptionList.action_page_down lacks a return annotation; the call is safe
        self.query_one(OptionList).action_page_down()  # type: ignore[no-untyped-call]

    def action_first(self) -> None:
        """Jump the list highlight to the first option without leaving the input."""
        self.query_one(OptionList).action_first()

    def action_last(self) -> None:
        """Jump the list highlight to the last option without leaving the input."""
        self.query_one(OptionList).action_last()
