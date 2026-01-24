"""Tests for enums.config_level module."""

from foxhole_stockpiles.enums.config_level import ConfigLevel


class TestConfigLevel:
    """Test suite for ConfigLevel enum."""

    def test_enum_values(self) -> None:
        """Test that enum values match expected strings."""
        assert ConfigLevel.BASIC.value == "basic"
        assert ConfigLevel.ADVANCED.value == "advanced"
        assert ConfigLevel.DEVELOPER.value == "developer"

    def test_enum_is_str(self) -> None:
        """Test that enum inherits from str."""
        assert isinstance(ConfigLevel.BASIC, str)
        assert isinstance(ConfigLevel.ADVANCED, str)
        assert isinstance(ConfigLevel.DEVELOPER, str)

    def test_enum_order(self) -> None:
        """Test that enum members are in correct order."""
        members = list(ConfigLevel)
        assert members[0] == ConfigLevel.BASIC
        assert members[1] == ConfigLevel.ADVANCED
        assert members[2] == ConfigLevel.DEVELOPER

    def test_is_at_least_basic(self) -> None:
        """Test is_at_least with BASIC level."""
        assert ConfigLevel.BASIC.is_at_least(ConfigLevel.BASIC) is True
        assert ConfigLevel.BASIC.is_at_least(ConfigLevel.ADVANCED) is False
        assert ConfigLevel.BASIC.is_at_least(ConfigLevel.DEVELOPER) is False

    def test_is_at_least_advanced(self) -> None:
        """Test is_at_least with ADVANCED level."""
        assert ConfigLevel.ADVANCED.is_at_least(ConfigLevel.BASIC) is True
        assert ConfigLevel.ADVANCED.is_at_least(ConfigLevel.ADVANCED) is True
        assert ConfigLevel.ADVANCED.is_at_least(ConfigLevel.DEVELOPER) is False

    def test_is_at_least_developer(self) -> None:
        """Test is_at_least with DEVELOPER level."""
        assert ConfigLevel.DEVELOPER.is_at_least(ConfigLevel.BASIC) is True
        assert ConfigLevel.DEVELOPER.is_at_least(ConfigLevel.ADVANCED) is True
        assert ConfigLevel.DEVELOPER.is_at_least(ConfigLevel.DEVELOPER) is True

    def test_string_comparison(self) -> None:
        """Test that enum values match their string values."""
        assert ConfigLevel.BASIC.value == "basic"
        assert ConfigLevel.ADVANCED.value == "advanced"
        assert ConfigLevel.DEVELOPER.value == "developer"

    def test_enum_from_string(self) -> None:
        """Test creating enum from string value."""
        assert ConfigLevel("basic") == ConfigLevel.BASIC
        assert ConfigLevel("advanced") == ConfigLevel.ADVANCED
        assert ConfigLevel("developer") == ConfigLevel.DEVELOPER
