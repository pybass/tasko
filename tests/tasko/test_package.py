"""Package-level smoke test."""

import tasko


class TestPackage:
    """Package-level sanity checks."""

    def test_import(self) -> None:
        """The package imports cleanly."""
        assert tasko.__doc__
