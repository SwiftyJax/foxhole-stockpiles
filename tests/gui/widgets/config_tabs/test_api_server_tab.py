"""Tests for APIServerTab."""

import json
from typing import Any

import pytest
from PyQt6.QtWidgets import QLineEdit

from foxhole_stockpiles.core.settings.sections.api import APIAuthSettings, APIServerSettings
from foxhole_stockpiles.enums.auth_type import AuthType
from foxhole_stockpiles.enums.config_level import ConfigLevel
from foxhole_stockpiles.gui.widgets.config_tabs.api_server_tab import APIServerTab


@pytest.fixture
def api_server_tab(qtbot: Any) -> APIServerTab:
    """Create an APIServerTab instance.

    Args:
        qtbot: PyQt test fixture

    Returns:
        APIServerTab: Tab instance
    """
    tab = APIServerTab()
    qtbot.addWidget(tab)
    return tab


def test_api_server_tab_initialization(api_server_tab: APIServerTab) -> None:
    """Test APIServerTab initialization.

    Args:
        api_server_tab: APIServerTab instance
    """
    assert api_server_tab.host_input is not None
    assert api_server_tab.port_input is not None
    assert api_server_tab.workers_input is not None
    assert api_server_tab.cors_input is not None
    assert api_server_tab.memory_monitoring_input is not None
    assert api_server_tab.auto_trim_input is not None


def test_api_server_tab_default_values(api_server_tab: APIServerTab) -> None:
    """Test default values are set correctly.

    Args:
        api_server_tab: APIServerTab instance
    """
    assert api_server_tab.port_input.value() == 8000
    assert api_server_tab.workers_input.value() == 1
    assert api_server_tab.auto_trim_input.isChecked()


def test_api_server_tab_port_range(api_server_tab: APIServerTab) -> None:
    """Test port input has correct range.

    Args:
        api_server_tab: APIServerTab instance
    """
    assert api_server_tab.port_input.minimum() == 1
    assert api_server_tab.port_input.maximum() == 65535


def test_api_server_tab_workers_range(api_server_tab: APIServerTab) -> None:
    """Test workers input has correct range.

    Args:
        api_server_tab: APIServerTab instance
    """
    assert api_server_tab.workers_input.minimum() == 1
    assert api_server_tab.workers_input.maximum() == 32


def test_api_server_tab_set_values(api_server_tab: APIServerTab) -> None:
    """Test setting values from settings object.

    Args:
        api_server_tab: APIServerTab instance
    """
    settings = APIServerSettings(
        host="192.168.1.100",
        port=9000,
        workers=4,
        cors_allow_origins=["http://localhost:3000", "http://example.com"],
        enable_memory_monitoring=True,
        auto_trim_memory=False,
    )

    api_server_tab.set_values(settings)

    assert api_server_tab.host_input.text() == "192.168.1.100"
    assert api_server_tab.port_input.value() == 9000
    assert api_server_tab.workers_input.value() == 4
    assert api_server_tab.memory_monitoring_input.isChecked()
    assert not api_server_tab.auto_trim_input.isChecked()

    # Check CORS is formatted as JSON
    cors_text = api_server_tab.cors_input.toPlainText()
    cors_list = json.loads(cors_text)
    assert cors_list == ["http://localhost:3000", "http://example.com"]


def test_api_server_tab_set_values_wildcard_cors(api_server_tab: APIServerTab) -> None:
    """Test setting values with wildcard CORS.

    Args:
        api_server_tab: APIServerTab instance
    """
    settings = APIServerSettings(cors_allow_origins=["*"])

    api_server_tab.set_values(settings)

    cors_text = api_server_tab.cors_input.toPlainText()
    cors_list = json.loads(cors_text)
    assert cors_list == ["*"]


def test_api_server_tab_get_values(api_server_tab: APIServerTab) -> None:
    """Test getting values from widgets.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.host_input.setText("10.0.0.1")
    api_server_tab.port_input.setValue(5000)
    api_server_tab.workers_input.setValue(2)
    api_server_tab.cors_input.setPlainText('["http://localhost:8080"]')
    api_server_tab.memory_monitoring_input.setChecked(False)
    api_server_tab.auto_trim_input.setChecked(True)

    settings = api_server_tab.get_server_values()

    assert settings.host == "10.0.0.1"
    assert settings.port == 5000
    assert settings.workers == 2
    assert settings.cors_allow_origins == ["http://localhost:8080"]
    assert not settings.enable_memory_monitoring
    assert settings.auto_trim_memory
    assert settings.log_level == "info"
    assert settings.reload is False


def test_api_server_tab_get_values_invalid_json_cors(api_server_tab: APIServerTab) -> None:
    """Test getting values with invalid JSON CORS falls back to wildcard.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.cors_input.setPlainText("not valid json")

    settings = api_server_tab.get_server_values()

    # Should fall back to wildcard
    assert settings.cors_allow_origins == ["*"]


def test_api_server_tab_get_values_empty_cors(api_server_tab: APIServerTab) -> None:
    """Test getting values with empty CORS input.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.cors_input.setPlainText("")

    settings = api_server_tab.get_server_values()

    # Should fall back to wildcard
    assert settings.cors_allow_origins == ["*"]


def test_api_server_tab_cors_pretty_format(api_server_tab: APIServerTab) -> None:
    """Test CORS is formatted with indentation.

    Args:
        api_server_tab: APIServerTab instance
    """
    settings = APIServerSettings(cors_allow_origins=["http://a.com", "http://b.com"])

    api_server_tab.set_values(settings)

    cors_text = api_server_tab.cors_input.toPlainText()
    # Should have newlines for pretty formatting
    assert "\n" in cors_text
    # Should be valid JSON
    cors_list = json.loads(cors_text)
    assert len(cors_list) == 2


def test_api_server_tab_memory_monitoring_checkbox(api_server_tab: APIServerTab) -> None:
    """Test memory monitoring checkbox behavior.

    Args:
        api_server_tab: APIServerTab instance
    """
    # Should be unchecked by default
    api_server_tab.memory_monitoring_input.setChecked(True)
    assert api_server_tab.memory_monitoring_input.isChecked()

    api_server_tab.memory_monitoring_input.setChecked(False)
    assert not api_server_tab.memory_monitoring_input.isChecked()


def test_api_server_tab_auto_trim_checkbox(api_server_tab: APIServerTab) -> None:
    """Test auto trim checkbox behavior.

    Args:
        api_server_tab: APIServerTab instance
    """
    # Should be checked by default
    assert api_server_tab.auto_trim_input.isChecked()

    api_server_tab.auto_trim_input.setChecked(False)
    assert not api_server_tab.auto_trim_input.isChecked()


def test_api_server_tab_set_values_default_settings(api_server_tab: APIServerTab) -> None:
    """Test setting values with default settings object.

    Args:
        api_server_tab: APIServerTab instance
    """
    settings = APIServerSettings()

    api_server_tab.set_values(settings)

    assert api_server_tab.host_input.text() == settings.host
    assert api_server_tab.port_input.value() == settings.port
    assert api_server_tab.workers_input.value() == settings.workers


def test_api_server_tab_cors_multiline_format(api_server_tab: APIServerTab) -> None:
    """Test CORS input shows multiline format.

    Args:
        api_server_tab: APIServerTab instance
    """
    settings = APIServerSettings(
        cors_allow_origins=["http://one.com", "http://two.com", "http://three.com"]
    )

    api_server_tab.set_values(settings)

    cors_text = api_server_tab.cors_input.toPlainText()
    lines = cors_text.split("\n")
    # Should have multiple lines due to JSON formatting
    assert len(lines) > 1


def test_api_server_tab_get_values_whitespace_in_host(api_server_tab: APIServerTab) -> None:
    """Test getting values with whitespace in host.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.host_input.setText("  192.168.1.1  ")

    settings = api_server_tab.get_server_values()

    # Should preserve whitespace (validation happens in pydantic model)
    assert settings.host == "  192.168.1.1  "


def test_api_server_tab_reload_always_false(api_server_tab: APIServerTab) -> None:
    """Test reload is always False in GUI mode.

    Args:
        api_server_tab: APIServerTab instance
    """
    settings = api_server_tab.get_server_values()

    assert settings.reload is False


def test_api_server_tab_log_level_always_info(api_server_tab: APIServerTab) -> None:
    """Test log_level is always 'info' (configured in logging tab: Any).

    Args:
        api_server_tab: APIServerTab instance
    """
    settings = api_server_tab.get_server_values()

    assert settings.log_level == "info"


def test_api_server_tab_cors_single_origin(api_server_tab: APIServerTab) -> None:
    """Test CORS with single origin.

    Args:
        api_server_tab: APIServerTab instance
    """
    settings = APIServerSettings(cors_allow_origins=["http://single.com"])

    api_server_tab.set_values(settings)

    cors_text = api_server_tab.cors_input.toPlainText()
    cors_list = json.loads(cors_text)
    assert cors_list == ["http://single.com"]


def test_api_server_tab_cors_empty_list(api_server_tab: APIServerTab) -> None:
    """Test CORS with empty list.

    Args:
        api_server_tab: APIServerTab instance
    """
    settings = APIServerSettings(cors_allow_origins=[])

    api_server_tab.set_values(settings)

    cors_text = api_server_tab.cors_input.toPlainText()
    cors_list = json.loads(cors_text)
    assert cors_list == []


def test_api_server_tab_max_workers_boundary(api_server_tab: APIServerTab) -> None:
    """Test workers at maximum boundary.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.workers_input.setValue(32)

    settings = api_server_tab.get_server_values()

    assert settings.workers == 32


def test_api_server_tab_min_workers_boundary(api_server_tab: APIServerTab) -> None:
    """Test workers at minimum boundary.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.workers_input.setValue(1)

    settings = api_server_tab.get_server_values()

    assert settings.workers == 1


def test_api_server_tab_max_port_boundary(api_server_tab: APIServerTab) -> None:
    """Test port at maximum boundary.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.port_input.setValue(65535)

    settings = api_server_tab.get_server_values()

    assert settings.port == 65535


def test_api_server_tab_min_port_boundary(api_server_tab: APIServerTab) -> None:
    """Test port at minimum boundary.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.port_input.setValue(1)

    settings = api_server_tab.get_server_values()

    assert settings.port == 1


# ===== Authentication Tests =====


def test_api_server_tab_auth_initialization(api_server_tab: APIServerTab) -> None:
    """Test APIServerTab auth components initialization.

    Args:
        api_server_tab: APIServerTab instance
    """
    assert api_server_tab.auth_type_button_group is not None
    assert api_server_tab.no_auth_radio is not None
    assert api_server_tab.basic_auth_radio is not None
    assert api_server_tab.bearer_auth_radio is not None
    assert api_server_tab.basic_auth_widget is not None
    assert api_server_tab.bearer_auth_widget is not None


def test_api_server_tab_default_no_auth(api_server_tab: APIServerTab) -> None:
    """Test default is no authentication.

    Args:
        api_server_tab: APIServerTab instance
    """
    assert api_server_tab.no_auth_radio.isChecked()
    assert not api_server_tab.basic_auth_radio.isChecked()
    assert not api_server_tab.bearer_auth_radio.isChecked()


def test_api_server_tab_no_auth_hides_widgets(api_server_tab: APIServerTab) -> None:
    """Test no auth hides credential widgets.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.no_auth_radio.setChecked(True)
    api_server_tab._update_auth_visibility()

    assert not api_server_tab.basic_auth_widget.isVisible()
    assert not api_server_tab.bearer_auth_widget.isVisible()


def test_api_server_tab_basic_auth_shows_basic_widget(api_server_tab: APIServerTab) -> None:
    """Test basic auth shows basic widget only.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.show()  # Show widget first
    api_server_tab.basic_auth_radio.setChecked(True)
    api_server_tab._update_auth_visibility()

    assert api_server_tab.basic_auth_widget.isVisible()
    assert not api_server_tab.bearer_auth_widget.isVisible()


def test_api_server_tab_bearer_auth_shows_bearer_widget(api_server_tab: APIServerTab) -> None:
    """Test bearer auth shows bearer widget only.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.show()  # Show widget first
    api_server_tab.bearer_auth_radio.setChecked(True)
    api_server_tab._update_auth_visibility()

    assert not api_server_tab.basic_auth_widget.isVisible()
    assert api_server_tab.bearer_auth_widget.isVisible()


def test_api_server_tab_set_values_no_auth(api_server_tab: APIServerTab) -> None:
    """Test setting values with no auth.

    Args:
        api_server_tab: APIServerTab instance
    """
    server_settings = APIServerSettings()
    auth_settings = APIAuthSettings(auth_type=None, auth_token=None)

    api_server_tab.set_values(server_settings, auth_settings)

    assert api_server_tab.no_auth_radio.isChecked()


def test_api_server_tab_set_values_basic_auth(api_server_tab: APIServerTab) -> None:
    """Test setting values with basic auth.

    Args:
        api_server_tab: APIServerTab instance
    """
    server_settings = APIServerSettings()
    auth_settings = APIAuthSettings(auth_type=AuthType.BASIC, auth_token="user:pass")

    api_server_tab.set_values(server_settings, auth_settings)

    assert api_server_tab.basic_auth_radio.isChecked()
    assert api_server_tab.basic_username_input.text() == "user"
    assert api_server_tab.basic_password_input.text() == "pass"


def test_api_server_tab_set_values_basic_auth_no_colon(api_server_tab: APIServerTab) -> None:
    """Test setting values with basic auth token without colon.

    Args:
        api_server_tab: APIServerTab instance
    """
    server_settings = APIServerSettings()
    auth_settings = APIAuthSettings(auth_type=AuthType.BASIC, auth_token="invalidtoken")

    api_server_tab.set_values(server_settings, auth_settings)

    assert api_server_tab.basic_auth_radio.isChecked()
    assert api_server_tab.basic_username_input.text() == "invalidtoken"
    assert api_server_tab.basic_password_input.text() == ""


def test_api_server_tab_set_values_bearer_auth(api_server_tab: APIServerTab) -> None:
    """Test setting values with bearer auth.

    Args:
        api_server_tab: APIServerTab instance
    """
    server_settings = APIServerSettings()
    auth_settings = APIAuthSettings(auth_type=AuthType.BEARER, auth_token="secret-token-123")

    api_server_tab.set_values(server_settings, auth_settings)

    assert api_server_tab.bearer_auth_radio.isChecked()
    assert api_server_tab.bearer_token_input.text() == "secret-token-123"


def test_api_server_tab_get_auth_values_no_auth(api_server_tab: APIServerTab) -> None:
    """Test getting auth values with no auth.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.no_auth_radio.setChecked(True)

    settings = api_server_tab.get_auth_values()

    assert settings.auth_type is None
    assert settings.auth_token is None


def test_api_server_tab_get_auth_values_basic_auth(api_server_tab: APIServerTab) -> None:
    """Test getting auth values with basic auth.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.basic_auth_radio.setChecked(True)
    api_server_tab.basic_username_input.setText("testuser")
    api_server_tab.basic_password_input.setText("testpass")

    settings = api_server_tab.get_auth_values()

    assert settings.auth_type == AuthType.BASIC
    assert settings.auth_token == "testuser:testpass"


def test_api_server_tab_get_auth_values_basic_auth_empty_credentials(
    api_server_tab: APIServerTab,
) -> None:
    """Test getting auth values with basic auth but empty credentials falls back to no auth.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.basic_auth_radio.setChecked(True)
    api_server_tab.basic_username_input.setText("")
    api_server_tab.basic_password_input.setText("")

    settings = api_server_tab.get_auth_values()

    # Empty credentials means no token, so auth_type should also be None
    assert settings.auth_type is None
    assert settings.auth_token is None


def test_api_server_tab_get_auth_values_basic_auth_whitespace_only(
    api_server_tab: APIServerTab,
) -> None:
    """Test getting auth values with whitespace-only credentials falls back to no auth.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.basic_auth_radio.setChecked(True)
    api_server_tab.basic_username_input.setText("   ")
    api_server_tab.basic_password_input.setText("   ")

    settings = api_server_tab.get_auth_values()

    # Whitespace gets stripped, so no token, and auth_type should also be None
    assert settings.auth_type is None
    assert settings.auth_token is None


def test_api_server_tab_get_auth_values_bearer_auth(api_server_tab: APIServerTab) -> None:
    """Test getting auth values with bearer auth.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.bearer_auth_radio.setChecked(True)
    api_server_tab.bearer_token_input.setText("my-secret-token")

    settings = api_server_tab.get_auth_values()

    assert settings.auth_type == AuthType.BEARER
    assert settings.auth_token == "my-secret-token"


def test_api_server_tab_get_auth_values_bearer_auth_empty_token(
    api_server_tab: APIServerTab,
) -> None:
    """Test getting auth values with bearer auth but empty token falls back to no auth.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.bearer_auth_radio.setChecked(True)
    api_server_tab.bearer_token_input.setText("")

    settings = api_server_tab.get_auth_values()

    # Empty token means auth_type should also be None
    assert settings.auth_type is None
    assert settings.auth_token is None


def test_api_server_tab_get_auth_values_bearer_auth_whitespace_only(
    api_server_tab: APIServerTab,
) -> None:
    """Test getting auth values with whitespace-only token falls back to no auth.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.bearer_auth_radio.setChecked(True)
    api_server_tab.bearer_token_input.setText("   ")

    settings = api_server_tab.get_auth_values()

    # Whitespace gets stripped, so no token, and auth_type should also be None
    assert settings.auth_type is None
    assert settings.auth_token is None


def test_api_server_tab_password_echo_mode(api_server_tab: APIServerTab) -> None:
    """Test that password fields use password echo mode.

    Args:
        api_server_tab: APIServerTab instance
    """
    assert api_server_tab.basic_password_input.echoMode() == QLineEdit.EchoMode.Password
    assert api_server_tab.bearer_token_input.echoMode() == QLineEdit.EchoMode.Password


def test_api_server_tab_radio_button_signal_updates_visibility(
    qtbot: Any, api_server_tab: APIServerTab
) -> None:
    """Test radio button change triggers visibility update.

    Args:
        qtbot: PyQt test fixture
        api_server_tab: APIServerTab instance
    """
    api_server_tab.show()  # Show widget first

    # Start with no auth
    assert api_server_tab.no_auth_radio.isChecked()
    assert not api_server_tab.basic_auth_widget.isVisible()

    # Switch to basic auth - need to trigger the signal manually
    api_server_tab.basic_auth_radio.click()

    # Should show basic auth widget
    assert api_server_tab.basic_auth_widget.isVisible()
    assert not api_server_tab.bearer_auth_widget.isVisible()


def test_api_server_tab_set_values_null_auth_type_string(api_server_tab: APIServerTab) -> None:
    """Test setting values with None as auth type.

    Args:
        api_server_tab: APIServerTab instance
    """
    server_settings = APIServerSettings()
    auth_settings = APIAuthSettings(auth_type=None, auth_token=None)

    api_server_tab.set_values(server_settings, auth_settings)

    assert api_server_tab.no_auth_radio.isChecked()


def test_api_server_tab_basic_auth_with_username_only(api_server_tab: APIServerTab) -> None:
    """Test getting auth values with username but no password.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.basic_auth_radio.setChecked(True)
    api_server_tab.basic_username_input.setText("user")
    api_server_tab.basic_password_input.setText("")

    settings = api_server_tab.get_auth_values()

    assert settings.auth_type == AuthType.BASIC
    assert settings.auth_token == "user:"


def test_api_server_tab_basic_auth_with_password_only(api_server_tab: APIServerTab) -> None:
    """Test getting auth values with password but no username.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.basic_auth_radio.setChecked(True)
    api_server_tab.basic_username_input.setText("")
    api_server_tab.basic_password_input.setText("pass")

    settings = api_server_tab.get_auth_values()

    assert settings.auth_type == AuthType.BASIC
    assert settings.auth_token == ":pass"


def test_api_server_tab_set_values_with_colon_in_password(api_server_tab: APIServerTab) -> None:
    """Test setting values when password contains colon.

    Args:
        api_server_tab: APIServerTab instance
    """
    server_settings = APIServerSettings()
    auth_settings = APIAuthSettings(auth_type=AuthType.BASIC, auth_token="user:pass:with:colons")

    api_server_tab.set_values(server_settings, auth_settings)

    assert api_server_tab.basic_username_input.text() == "user"
    assert api_server_tab.basic_password_input.text() == "pass:with:colons"


def test_api_server_tab_button_group_has_correct_ids(api_server_tab: APIServerTab) -> None:
    """Test button group has correct IDs assigned.

    Args:
        api_server_tab: APIServerTab instance
    """
    assert api_server_tab.auth_type_button_group.id(api_server_tab.no_auth_radio) == 0
    assert api_server_tab.auth_type_button_group.id(api_server_tab.basic_auth_radio) == 1
    assert api_server_tab.auth_type_button_group.id(api_server_tab.bearer_auth_radio) == 2


def test_api_server_tab_set_values_empty_token_basic(api_server_tab: APIServerTab) -> None:
    """Test setting values with None for both auth_type and token.

    Args:
        api_server_tab: APIServerTab instance
    """
    server_settings = APIServerSettings()
    auth_settings = APIAuthSettings(auth_type=None, auth_token=None)

    api_server_tab.set_values(server_settings, auth_settings)

    # Should select no auth when both are None
    assert api_server_tab.no_auth_radio.isChecked()


def test_api_server_tab_set_values_empty_token_bearer(api_server_tab: APIServerTab) -> None:
    """Test setting values with valid bearer auth and token.

    Args:
        api_server_tab: APIServerTab instance
    """
    server_settings = APIServerSettings()
    auth_settings = APIAuthSettings(auth_type=AuthType.BEARER, auth_token="test-token")

    api_server_tab.set_values(server_settings, auth_settings)

    assert api_server_tab.bearer_auth_radio.isChecked()
    assert api_server_tab.bearer_token_input.text() == "test-token"


def test_api_server_tab_set_config_level_basic(api_server_tab: APIServerTab) -> None:
    """Test set_config_level with BASIC level hides CORS field.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.set_config_level(ConfigLevel.BASIC)

    # Use isHidden() instead of isVisible() since parent widget is not shown
    # CORS widgets should be hidden
    assert api_server_tab._cors_label.isHidden()
    assert api_server_tab.cors_input.isHidden()


def test_api_server_tab_set_config_level_advanced(api_server_tab: APIServerTab) -> None:
    """Test set_config_level with ADVANCED level shows CORS field.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.set_config_level(ConfigLevel.ADVANCED)

    # Use isHidden() instead of isVisible() since parent widget is not shown
    # CORS widgets should be visible
    assert not api_server_tab._cors_label.isHidden()
    assert not api_server_tab.cors_input.isHidden()


def test_api_server_tab_set_config_level_developer(api_server_tab: APIServerTab) -> None:
    """Test set_config_level with DEVELOPER level shows CORS field.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.set_config_level(ConfigLevel.DEVELOPER)

    # Use isHidden() instead of isVisible() since parent widget is not shown
    # CORS widgets should be visible
    assert not api_server_tab._cors_label.isHidden()
    assert not api_server_tab.cors_input.isHidden()


def test_api_server_tab_config_level_transition(api_server_tab: APIServerTab) -> None:
    """Test transitioning between config levels.

    Args:
        api_server_tab: APIServerTab instance
    """
    # Use isHidden() instead of isVisible() since parent widget is not shown

    # Start with advanced
    api_server_tab.set_config_level(ConfigLevel.ADVANCED)
    assert not api_server_tab._cors_label.isHidden()

    # Transition to basic
    api_server_tab.set_config_level(ConfigLevel.BASIC)
    assert api_server_tab._cors_label.isHidden()

    # Back to advanced
    api_server_tab.set_config_level(ConfigLevel.ADVANCED)
    assert not api_server_tab._cors_label.isHidden()
