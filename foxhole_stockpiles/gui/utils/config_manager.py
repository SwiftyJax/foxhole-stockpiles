"""Configuration manager for loading and saving settings."""

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from foxhole_stockpiles.core.settings import get_settings
from foxhole_stockpiles.core.settings.app_settings import AppSettings

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages loading and saving of application configuration."""

    def __init__(self) -> None:
        """Initialize the configuration manager."""
        self.config_path = Path("~/.fs_config").expanduser()

    def load_config(self) -> AppSettings:
        """Load configuration from file or create default.

        Returns:
            AppSettings: Loaded configuration or default if loading fails.
        """
        try:
            settings = get_settings()
            logger.info("Configuration loaded successfully from %s", self.config_path)
            return settings
        except Exception as e:
            logger.warning("Failed to load config, using defaults: %s", e)
            return AppSettings()

    def save_config(self, settings: AppSettings) -> tuple[bool, str]:
        """Save configuration to file.

        Args:
            settings (AppSettings): AppSettings instance to save.

        Returns:
            tuple[bool, str]: Tuple of (success, message).
        """
        try:
            # Convert settings to dict
            config_dict = settings.model_dump(mode="json", exclude_none=False)

            # Save to file with pretty printing
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)

            logger.info("Configuration saved successfully to %s", self.config_path)
            return True, f"Configuration saved to {self.config_path}"

        except Exception as e:
            error_msg = f"Failed to save configuration: {e}"
            logger.error(error_msg)
            return False, error_msg

    def validate_config(self, config_dict: dict[str, Any]) -> tuple[bool, str, AppSettings | None]:
        """Validate configuration dictionary.

        Args:
            config_dict (dict[str, Any]): Configuration dictionary to validate.

        Returns:
            tuple[bool, str, AppSettings | None]: Tuple of (valid, message, settings).
        """
        try:
            settings = AppSettings(**config_dict)
            return True, "Configuration is valid", settings
        except ValidationError as e:
            error_msg = f"Configuration validation failed:\n{e}"
            logger.error(error_msg)
            return False, error_msg, None
        except Exception as e:
            error_msg = f"Unexpected error during validation: {e}"
            logger.error(error_msg)
            return False, error_msg, None

    def export_config(self, filepath: Path, settings: AppSettings) -> tuple[bool, str]:
        """Export configuration to a specific file.

        Args:
            filepath (Path): Path to export configuration to.
            settings (AppSettings): AppSettings instance to export.

        Returns:
            tuple[bool, str]: Tuple of (success, message).
        """
        try:
            config_dict = settings.model_dump(mode="json", exclude_none=False)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)

            logger.info("Configuration exported to %s", filepath)
            return True, f"Configuration exported to {filepath}"

        except Exception as e:
            error_msg = f"Failed to export configuration: {e}"
            logger.error(error_msg)
            return False, error_msg

    def import_config(self, filepath: Path) -> tuple[bool, str, AppSettings | None]:
        """Import configuration from a specific file.

        Args:
            filepath (Path): Path to import configuration from.

        Returns:
            tuple[bool, str, AppSettings | None]: Tuple of (success, message, settings).
        """
        try:
            with open(filepath, encoding="utf-8") as f:
                config_dict = json.load(f)

            valid, msg, settings = self.validate_config(config_dict)
            if not valid:
                return False, msg, None

            logger.info("Configuration imported from %s", filepath)
            return True, f"Configuration imported from {filepath}", settings

        except Exception as e:
            error_msg = f"Failed to import configuration: {e}"
            logger.error(error_msg)
            return False, error_msg, None
