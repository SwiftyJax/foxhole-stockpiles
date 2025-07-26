"""Logging configuration for Foxhole Stockpiles."""

import logging
import sys
from collections.abc import Sequence
from pathlib import Path


def setup_logging(
    log_level: int = logging.INFO,
    log_file: str = "",
    format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
) -> None:
    """Setup logging configuration for the application.

    Args:
        log_level (int): Logging level (default: INFO)
        log_file (str): Path to log file (default: empty string for no file logging)
        format_string (str): Custom format string (default: standard format)
    """
    handlers: Sequence[logging.Handler]
    if log_file:
        # Convert to Path and ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers = [logging.FileHandler(log_path)]
    else:
        handlers = [logging.StreamHandler(sys.stdout)]

    logging.basicConfig(
        level=log_level,
        format=format_string,
        handlers=handlers,
        force=True,
    )
