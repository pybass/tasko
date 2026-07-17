"""Application errors shared by all adapters."""


class AppError(Exception):
    """Business-rule violation or bad input; adapters show the message to the user."""
