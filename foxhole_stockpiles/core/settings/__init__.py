"""Configuration module for the app."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic_settings import InitSettingsSource, JsonConfigSettingsSource

from foxhole_stockpiles.core.settings.app_settings import AppSettings


class MigratingInitSettingsSource(InitSettingsSource):
    """Init settings source that applies migrations before validation."""

    def __call__(self) -> dict[str, Any]:
        """Get init settings with migrations applied.

        Returns:
            dict[str, Any]: Settings dictionary with migrations applied
        """
        data = super().__call__()
        if data and isinstance(data, dict):
            return AppSettings._apply_migrations(data)
        return data


class Utf8JsonConfigSettingsSource(JsonConfigSettingsSource):
    """JSON config settings source that reads files with UTF-8 encoding."""

    def _read_file(self, file_path: Path) -> dict[str, Any]:
        """Read and parse a JSON file with UTF-8 encoding.

        Args:
            file_path: Path to the JSON file

        Returns:
            dict[str, Any]: The parsed JSON data with migrations applied
        """
        with file_path.open("r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            # Apply migrations before returning
            return AppSettings._apply_migrations(data)

    def __call__(self) -> dict[str, Any]:
        """Get settings from JSON file with migrations applied.

        Returns:
            dict[str, Any]: Settings dictionary with migrations applied
        """
        data = super().__call__()
        if data:
            return AppSettings._apply_migrations(data)
        return data


@lru_cache
def get_settings() -> AppSettings:
    """Get the settings.

    Returns:
        AppSettings: The settings
    """
    return AppSettings()


def reload_settings() -> AppSettings:
    """Reload the settings by clearing the cache.

    Returns:
        AppSettings: Newly loaded settings
    """
    get_settings.cache_clear()
    return get_settings()


__all__ = [
    "AppSettings",
    "MigratingInitSettingsSource",
    "Utf8JsonConfigSettingsSource",
    "get_settings",
    "reload_settings",
]
