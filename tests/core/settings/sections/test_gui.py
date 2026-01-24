"""Tests for GUISettings."""

import pytest
from pydantic import ValidationError

from foxhole_stockpiles.core.settings.sections.gui import GUISettings
from foxhole_stockpiles.enums.config_level import ConfigLevel


class TestGUISettings:
    """Test suite for GUISettings."""

    def test_default_values(self) -> None:
        """Test default values are correct."""
        settings = GUISettings()

        assert settings.config_level == ConfigLevel.BASIC
        assert settings.minimize_to_tray is False

    def test_config_level_basic(self) -> None:
        """Test setting config level to basic."""
        settings = GUISettings(config_level=ConfigLevel.BASIC)

        assert settings.config_level == ConfigLevel.BASIC

    def test_config_level_advanced(self) -> None:
        """Test setting config level to advanced."""
        settings = GUISettings(config_level=ConfigLevel.ADVANCED)

        assert settings.config_level == ConfigLevel.ADVANCED

    def test_config_level_developer(self) -> None:
        """Test setting config level to developer."""
        settings = GUISettings(config_level=ConfigLevel.DEVELOPER)

        assert settings.config_level == ConfigLevel.DEVELOPER

    def test_config_level_from_string(self) -> None:
        """Test config level can be set from string."""
        settings = GUISettings(config_level="advanced")  # type: ignore[arg-type]

        assert settings.config_level == ConfigLevel.ADVANCED

    def test_config_level_invalid(self) -> None:
        """Test invalid config level raises validation error."""
        with pytest.raises(ValidationError):
            GUISettings(config_level="invalid")  # type: ignore[arg-type]

    def test_minimize_to_tray_true(self) -> None:
        """Test minimize to tray enabled."""
        settings = GUISettings(minimize_to_tray=True)

        assert settings.minimize_to_tray is True

    def test_minimize_to_tray_false(self) -> None:
        """Test minimize to tray disabled."""
        settings = GUISettings(minimize_to_tray=False)

        assert settings.minimize_to_tray is False

    def test_full_settings(self) -> None:
        """Test setting all values."""
        settings = GUISettings(
            config_level=ConfigLevel.DEVELOPER,
            minimize_to_tray=True,
        )

        assert settings.config_level == ConfigLevel.DEVELOPER
        assert settings.minimize_to_tray is True

    def test_extra_fields_forbidden(self) -> None:
        """Test extra fields are forbidden."""
        with pytest.raises(ValidationError):
            GUISettings(config_level=ConfigLevel.BASIC, unknown_field="value")  # type: ignore[call-arg]

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        settings = GUISettings(
            config_level=ConfigLevel.ADVANCED,
            minimize_to_tray=True,
        )

        json_str = settings.model_dump_json()
        assert "advanced" in json_str
        assert "true" in json_str.lower()

    def test_dict_serialization(self) -> None:
        """Test dict serialization."""
        settings = GUISettings(
            config_level=ConfigLevel.DEVELOPER,
            minimize_to_tray=False,
        )

        data = settings.model_dump()
        assert data["config_level"] == ConfigLevel.DEVELOPER
        assert data["minimize_to_tray"] is False

    def test_model_copy(self) -> None:
        """Test model copy with update."""
        settings = GUISettings(config_level=ConfigLevel.BASIC)

        updated = settings.model_copy(update={"config_level": ConfigLevel.ADVANCED})

        assert settings.config_level == ConfigLevel.BASIC
        assert updated.config_level == ConfigLevel.ADVANCED
