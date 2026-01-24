"""Enums for output formats."""

from enum import StrEnum


class OutputFormat(StrEnum):
    """Supported data serialization formats."""

    JSON = "json"
    CSV = "csv"
    TSV = "tsv"
