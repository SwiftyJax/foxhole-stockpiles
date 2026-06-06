"""Shared helpers for loading application settings in CLI commands."""

from foxhole_stockpiles.core.settings import AppSettings, get_settings


def get_app_settings(config_file: str | None = None) -> AppSettings:
    """Get application settings, optionally from a specified config file.

    Args:
        config_file (str | None): Path to the configuration file. If None, the
            default cached settings are returned.

    Returns:
        AppSettings: Application settings.
    """
    if config_file is None:
        return get_settings()

    # Per-instance env_file override (thread-safe; avoids mutating class-level
    # model_config, which would race across concurrent loads).
    return AppSettings(_env_file=config_file)
