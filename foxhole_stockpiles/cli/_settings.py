"""Shared helpers for loading application settings in CLI commands."""

import json
from pathlib import Path

from foxhole_stockpiles.core.settings import AppSettings, get_settings


def get_app_settings(config_file: str | None = None) -> AppSettings:
    """Get application settings, optionally from a specified JSON config file.

    When ``config_file`` is given it is parsed as JSON and passed to
    ``AppSettings`` as init values (highest-priority source), so its contents
    override the defaults and run through config migration.

    Args:
        config_file (str | None): Path to a JSON configuration file. If None,
            the default cached settings are returned.

    Returns:
        AppSettings: Application settings.

    Raises:
        FileNotFoundError: If config_file is given but does not exist.
        ValueError: If config_file is not valid JSON or is not a JSON object.
    """
    if config_file is None:
        return get_settings()

    path = Path(config_file)
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file {config_file}: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a JSON object: {config_file}")

    return AppSettings(**data)
