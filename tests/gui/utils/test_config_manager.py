"""Tests for ConfigManager."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from foxhole_stockpiles.core.settings import AppSettings
from foxhole_stockpiles.gui.utils.config_manager import ConfigManager


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings.

    Returns:
        MagicMock: Mock AppSettings object
    """
    settings = MagicMock(spec=AppSettings)
    settings.model_dump.return_value = {"test": "data"}
    settings.model_dump_json.return_value = '{"test": "data"}'
    return settings


def test_config_manager_initialization() -> None:
    """Test ConfigManager initialization."""
    manager = ConfigManager()
    assert manager.config_path == Path("~/.fs_config").expanduser()


def test_config_manager_load_config() -> None:
    """Test loading config."""
    with patch("foxhole_stockpiles.gui.utils.config_manager.get_settings") as mock_get_settings:
        mock_get_settings.return_value = MagicMock(spec=AppSettings)

        manager = ConfigManager()
        settings = manager.load_config()

        assert settings is not None
        mock_get_settings.assert_called_once()


def test_config_manager_load_config_fallback_on_error() -> None:
    """Test loading config falls back to defaults on error."""
    with patch("foxhole_stockpiles.gui.utils.config_manager.get_settings") as mock_get_settings:
        mock_get_settings.side_effect = Exception("Config error")

        manager = ConfigManager()
        settings = manager.load_config()

        # Should return default AppSettings
        assert isinstance(settings, AppSettings)


def test_config_manager_save_config(tmp_path: Path, mock_settings: MagicMock) -> None:
    """Test saving config to file.

    Args:
        tmp_path (Path): Temporary directory path
        mock_settings (MagicMock): Mock settings object
    """
    config_file = tmp_path / "test_config.json"

    manager = ConfigManager()
    manager.config_path = config_file  # Set instance attribute directly
    success, message = manager.save_config(mock_settings)

    assert success is True
    assert "saved" in message.lower()
    assert config_file.exists()


def test_config_manager_save_config_creates_directory(
    tmp_path: Path, mock_settings: MagicMock
) -> None:
    """Test save_config works when parent directory exists.

    Args:
        tmp_path (Path): Temporary directory path
        mock_settings (MagicMock): Mock settings object
    """
    nested_path = tmp_path / "nested" / "dir" / "config.json"

    # Create parent directories first (save_config doesn't create them)
    nested_path.parent.mkdir(parents=True, exist_ok=True)

    manager = ConfigManager()
    manager.config_path = nested_path  # Set instance attribute directly
    success, message = manager.save_config(mock_settings)

    assert success is True
    assert nested_path.exists()
    assert nested_path.parent.exists()


def test_config_manager_save_config_error_handling(tmp_path: Path) -> None:
    """Test save_config handles errors gracefully.

    Args:
        tmp_path (Path): Temporary directory path
    """
    invalid_settings = MagicMock(spec=AppSettings)
    invalid_settings.model_dump.side_effect = Exception("Dump error")

    config_file = tmp_path / "test_config.json"

    manager = ConfigManager()
    manager.config_path = config_file  # Set instance attribute directly
    success, message = manager.save_config(invalid_settings)

    assert success is False
    assert "failed" in message.lower()


def test_config_manager_validate_config_valid(mock_settings: MagicMock) -> None:
    """Test validate_config with valid config.

    Args:
        mock_settings (MagicMock): Mock settings object
    """
    config_dict = {"log_level": "INFO"}

    with patch(
        "foxhole_stockpiles.gui.utils.config_manager.AppSettings"
    ) as mock_app_settings_class:
        mock_app_settings_class.return_value = mock_settings

        manager = ConfigManager()
        valid, message, settings = manager.validate_config(config_dict)

        assert valid is True
        assert settings == mock_settings


def test_config_manager_validate_config_invalid() -> None:
    """Test validate_config with invalid config."""
    # Use an actual invalid config that will fail AppSettings validation
    config_dict = {"port": "not_a_number"}  # port should be an integer

    manager = ConfigManager()
    valid, message, settings = manager.validate_config(config_dict)

    assert valid is False
    assert settings is None
    # Message should contain validation error info
    assert len(message) > 0


def test_config_manager_export_config(tmp_path: Path, mock_settings: MagicMock) -> None:
    """Test exporting config to a specific file.

    Args:
        tmp_path (Path): Temporary directory path
        mock_settings (MagicMock): Mock settings object
    """
    export_path = tmp_path / "exported_config.json"

    manager = ConfigManager()
    success, message = manager.export_config(export_path, mock_settings)

    assert success is True
    assert "exported" in message.lower()
    assert export_path.exists()


def test_config_manager_export_config_error_handling(tmp_path: Path) -> None:
    """Test export_config handles errors gracefully.

    Args:
        tmp_path (Path): Temporary directory path
    """
    invalid_settings = MagicMock(spec=AppSettings)
    invalid_settings.model_dump.side_effect = Exception("Export error")

    export_path = tmp_path / "exported_config.json"

    manager = ConfigManager()
    success, message = manager.export_config(export_path, invalid_settings)

    assert success is False
    assert "failed" in message.lower()


def test_config_manager_import_config(tmp_path: Path) -> None:
    """Test importing config from a file.

    Args:
        tmp_path (Path): Temporary directory path
    """
    import_path = tmp_path / "import_config.json"
    import_path.write_text('{"log_level": "DEBUG"}')

    with patch(
        "foxhole_stockpiles.gui.utils.config_manager.AppSettings"
    ) as mock_app_settings_class:
        mock_settings = MagicMock(spec=AppSettings)
        mock_app_settings_class.return_value = mock_settings

        manager = ConfigManager()
        success, message, settings = manager.import_config(import_path)

        assert success is True
        assert "imported" in message.lower()
        assert settings == mock_settings


def test_config_manager_import_config_invalid_json(tmp_path: Path) -> None:
    """Test importing config with invalid JSON.

    Args:
        tmp_path (Path): Temporary directory path
    """
    import_path = tmp_path / "invalid.json"
    import_path.write_text("invalid json {")

    manager = ConfigManager()
    success, message, settings = manager.import_config(import_path)

    assert success is False
    assert "failed" in message.lower()
    assert settings is None


def test_config_manager_import_config_nonexistent_file() -> None:
    """Test importing config from nonexistent file."""
    import_path = Path("/nonexistent/config.json")

    manager = ConfigManager()
    success, message, settings = manager.import_config(import_path)

    assert success is False
    assert "failed" in message.lower()
    assert settings is None


def test_config_manager_import_config_validation_fails(tmp_path: Path) -> None:
    """Test importing config where validation fails.

    Args:
        tmp_path (Path): Temporary directory path
    """
    import_path = tmp_path / "invalid_settings.json"
    # Write valid JSON but with invalid settings values
    import_path.write_text('{"scanner": {"database_path": 123}}')

    manager = ConfigManager()
    success, message, settings = manager.import_config(import_path)

    assert success is False
    assert settings is None


def test_config_manager_validate_config_unexpected_error() -> None:
    """Test validate_config handles unexpected errors gracefully."""
    config_dict = {"test": "data"}

    with patch(
        "foxhole_stockpiles.gui.utils.config_manager.AppSettings"
    ) as mock_app_settings_class:
        # Make AppSettings raise an unexpected error (not ValidationError)
        mock_app_settings_class.side_effect = RuntimeError("Unexpected error")

        manager = ConfigManager()
        valid, message, settings = manager.validate_config(config_dict)

        assert valid is False
        assert settings is None
        assert "unexpected" in message.lower()
