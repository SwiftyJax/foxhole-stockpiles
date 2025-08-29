"""Enums for output formats."""

from enum import StrEnum


class OutputFormat(StrEnum):
    """Supported output formats for scanner results."""

    CONSOLE = "console"
    FILE = "file"
    JSON = "json"
    WEBHOOK = "webhook"
