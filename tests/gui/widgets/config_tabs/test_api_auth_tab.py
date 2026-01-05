"""Tests for APIAuthTab."""

from typing import Any

import pytest
from PyQt6.QtWidgets import QLineEdit

from foxhole_stockpiles.core.settings.sections.api import APIAuthSettings
from foxhole_stockpiles.enums.auth_type import AuthType
from foxhole_stockpiles.gui.widgets.config_tabs.api_auth_tab import APIAuthTab


@pytest.fixture
def api_auth_tab(qtbot: Any) -> APIAuthTab:
    """Create an APIAuthTab instance.

    Args:
        qtbot: PyQt test fixture

    Returns:
        APIAuthTab: Tab instance
    """
    tab = APIAuthTab()
    qtbot.addWidget(tab)
    return tab


def test_api_auth_tab_initialization(api_auth_tab: APIAuthTab) -> None:
    """Test APIAuthTab initialization.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    assert api_auth_tab.auth_type_button_group is not None
    assert api_auth_tab.no_auth_radio is not None
    assert api_auth_tab.basic_auth_radio is not None
    assert api_auth_tab.bearer_auth_radio is not None
    assert api_auth_tab.basic_auth_group is not None
    assert api_auth_tab.bearer_auth_group is not None


def test_api_auth_tab_default_no_auth(api_auth_tab: APIAuthTab) -> None:
    """Test default is no authentication.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    assert api_auth_tab.no_auth_radio.isChecked()
    assert not api_auth_tab.basic_auth_radio.isChecked()
    assert not api_auth_tab.bearer_auth_radio.isChecked()


def test_api_auth_tab_no_auth_hides_groups(api_auth_tab: APIAuthTab) -> None:
    """Test no auth hides credential groups.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    api_auth_tab.no_auth_radio.setChecked(True)
    api_auth_tab._update_auth_visibility()

    assert not api_auth_tab.basic_auth_group.isVisible()
    assert not api_auth_tab.bearer_auth_group.isVisible()


def test_api_auth_tab_basic_auth_shows_basic_group(api_auth_tab: APIAuthTab) -> None:
    """Test basic auth shows basic group only.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    api_auth_tab.show()  # Show widget first
    api_auth_tab.basic_auth_radio.setChecked(True)
    api_auth_tab._update_auth_visibility()

    assert api_auth_tab.basic_auth_group.isVisible()
    assert not api_auth_tab.bearer_auth_group.isVisible()


def test_api_auth_tab_bearer_auth_shows_bearer_group(api_auth_tab: APIAuthTab) -> None:
    """Test bearer auth shows bearer group only.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    api_auth_tab.show()  # Show widget first
    api_auth_tab.bearer_auth_radio.setChecked(True)
    api_auth_tab._update_auth_visibility()

    assert not api_auth_tab.basic_auth_group.isVisible()
    assert api_auth_tab.bearer_auth_group.isVisible()


def test_api_auth_tab_set_values_no_auth(api_auth_tab: APIAuthTab) -> None:
    """Test setting values with no auth.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    settings = APIAuthSettings(auth_type=None, auth_token=None)

    api_auth_tab.set_values(settings)

    assert api_auth_tab.no_auth_radio.isChecked()


def test_api_auth_tab_set_values_basic_auth(api_auth_tab: APIAuthTab) -> None:
    """Test setting values with basic auth.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    settings = APIAuthSettings(auth_type=AuthType.BASIC, auth_token="user:pass")

    api_auth_tab.set_values(settings)

    assert api_auth_tab.basic_auth_radio.isChecked()
    assert api_auth_tab.basic_username_input.text() == "user"
    assert api_auth_tab.basic_password_input.text() == "pass"


def test_api_auth_tab_set_values_basic_auth_no_colon(api_auth_tab: APIAuthTab) -> None:
    """Test setting values with basic auth token without colon.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    settings = APIAuthSettings(auth_type=AuthType.BASIC, auth_token="invalidtoken")

    api_auth_tab.set_values(settings)

    assert api_auth_tab.basic_auth_radio.isChecked()
    assert api_auth_tab.basic_username_input.text() == "invalidtoken"
    assert api_auth_tab.basic_password_input.text() == ""


def test_api_auth_tab_set_values_bearer_auth(api_auth_tab: APIAuthTab) -> None:
    """Test setting values with bearer auth.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    settings = APIAuthSettings(auth_type=AuthType.BEARER, auth_token="secret-token-123")

    api_auth_tab.set_values(settings)

    assert api_auth_tab.bearer_auth_radio.isChecked()
    assert api_auth_tab.bearer_token_input.text() == "secret-token-123"


def test_api_auth_tab_get_values_no_auth(api_auth_tab: APIAuthTab) -> None:
    """Test getting values with no auth.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    api_auth_tab.no_auth_radio.setChecked(True)

    settings = api_auth_tab.get_values()

    assert settings.auth_type is None
    assert settings.auth_token is None


def test_api_auth_tab_get_values_basic_auth(api_auth_tab: APIAuthTab) -> None:
    """Test getting values with basic auth.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    api_auth_tab.basic_auth_radio.setChecked(True)
    api_auth_tab.basic_username_input.setText("testuser")
    api_auth_tab.basic_password_input.setText("testpass")

    settings = api_auth_tab.get_values()

    assert settings.auth_type == AuthType.BASIC
    assert settings.auth_token == "testuser:testpass"


def test_api_auth_tab_get_values_basic_auth_empty_credentials(api_auth_tab: APIAuthTab) -> None:
    """Test getting values with basic auth but empty credentials falls back to no auth.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    api_auth_tab.basic_auth_radio.setChecked(True)
    api_auth_tab.basic_username_input.setText("")
    api_auth_tab.basic_password_input.setText("")

    settings = api_auth_tab.get_values()

    # Empty credentials means no token, so auth_type should also be None
    # (validation requires both to be set or both to be None)
    assert settings.auth_type is None
    assert settings.auth_token is None


def test_api_auth_tab_get_values_basic_auth_whitespace_only(api_auth_tab: APIAuthTab) -> None:
    """Test getting values with basic auth but whitespace-only credentials falls back to no auth.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    api_auth_tab.basic_auth_radio.setChecked(True)
    api_auth_tab.basic_username_input.setText("   ")
    api_auth_tab.basic_password_input.setText("   ")

    settings = api_auth_tab.get_values()

    # Whitespace gets stripped, so no token, and auth_type should also be None
    assert settings.auth_type is None
    assert settings.auth_token is None


def test_api_auth_tab_get_values_bearer_auth(api_auth_tab: APIAuthTab) -> None:
    """Test getting values with bearer auth.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    api_auth_tab.bearer_auth_radio.setChecked(True)
    api_auth_tab.bearer_token_input.setText("my-secret-token")

    settings = api_auth_tab.get_values()

    assert settings.auth_type == AuthType.BEARER
    assert settings.auth_token == "my-secret-token"


def test_api_auth_tab_get_values_bearer_auth_empty_token(api_auth_tab: APIAuthTab) -> None:
    """Test getting values with bearer auth but empty token falls back to no auth.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    api_auth_tab.bearer_auth_radio.setChecked(True)
    api_auth_tab.bearer_token_input.setText("")

    settings = api_auth_tab.get_values()

    # Empty token means auth_type should also be None
    assert settings.auth_type is None
    assert settings.auth_token is None


def test_api_auth_tab_get_values_bearer_auth_whitespace_only(api_auth_tab: APIAuthTab) -> None:
    """Test getting values with bearer auth but whitespace-only token falls back to no auth.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    api_auth_tab.bearer_auth_radio.setChecked(True)
    api_auth_tab.bearer_token_input.setText("   ")

    settings = api_auth_tab.get_values()

    # Whitespace gets stripped, so no token, and auth_type should also be None
    assert settings.auth_type is None
    assert settings.auth_token is None


def test_api_auth_tab_password_echo_mode(api_auth_tab: APIAuthTab) -> None:
    """Test that password fields use password echo mode.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    assert api_auth_tab.basic_password_input.echoMode() == QLineEdit.EchoMode.Password
    assert api_auth_tab.bearer_token_input.echoMode() == QLineEdit.EchoMode.Password


def test_api_auth_tab_radio_button_signal_updates_visibility(
    qtbot: Any, api_auth_tab: APIAuthTab
) -> None:
    """Test radio button change triggers visibility update.

    Args:
        qtbot: PyQt test fixture
        api_auth_tab: APIAuthTab instance
    """
    api_auth_tab.show()  # Show widget first

    # Start with no auth
    assert api_auth_tab.no_auth_radio.isChecked()
    assert not api_auth_tab.basic_auth_group.isVisible()

    # Switch to basic auth - need to trigger the signal manually
    api_auth_tab.basic_auth_radio.click()

    # Should show basic auth group
    assert api_auth_tab.basic_auth_group.isVisible()
    assert not api_auth_tab.bearer_auth_group.isVisible()


def test_api_auth_tab_set_values_null_auth_type_string(api_auth_tab: APIAuthTab) -> None:
    """Test setting values with "null" string as auth type.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    settings = APIAuthSettings(auth_type=None, auth_token=None)

    api_auth_tab.set_values(settings)

    assert api_auth_tab.no_auth_radio.isChecked()


def test_api_auth_tab_basic_auth_with_username_only(api_auth_tab: APIAuthTab) -> None:
    """Test getting values with username but no password.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    api_auth_tab.basic_auth_radio.setChecked(True)
    api_auth_tab.basic_username_input.setText("user")
    api_auth_tab.basic_password_input.setText("")

    settings = api_auth_tab.get_values()

    assert settings.auth_type == AuthType.BASIC
    assert settings.auth_token == "user:"


def test_api_auth_tab_basic_auth_with_password_only(api_auth_tab: APIAuthTab) -> None:
    """Test getting values with password but no username.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    api_auth_tab.basic_auth_radio.setChecked(True)
    api_auth_tab.basic_username_input.setText("")
    api_auth_tab.basic_password_input.setText("pass")

    settings = api_auth_tab.get_values()

    assert settings.auth_type == AuthType.BASIC
    assert settings.auth_token == ":pass"


def test_api_auth_tab_set_values_with_colon_in_password(api_auth_tab: APIAuthTab) -> None:
    """Test setting values when password contains colon.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    settings = APIAuthSettings(auth_type=AuthType.BASIC, auth_token="user:pass:with:colons")

    api_auth_tab.set_values(settings)

    assert api_auth_tab.basic_username_input.text() == "user"
    assert api_auth_tab.basic_password_input.text() == "pass:with:colons"


def test_api_auth_tab_button_group_has_correct_ids(api_auth_tab: APIAuthTab) -> None:
    """Test button group has correct IDs assigned.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    assert api_auth_tab.auth_type_button_group.id(api_auth_tab.no_auth_radio) == 0
    assert api_auth_tab.auth_type_button_group.id(api_auth_tab.basic_auth_radio) == 1
    assert api_auth_tab.auth_type_button_group.id(api_auth_tab.bearer_auth_radio) == 2


def test_api_auth_tab_set_values_empty_token_basic(api_auth_tab: APIAuthTab) -> None:
    """Test setting values with None for both auth_type and token.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    # Validation requires both to be None or both to be set
    settings = APIAuthSettings(auth_type=None, auth_token=None)

    api_auth_tab.set_values(settings)

    # Should select no auth when both are None
    assert api_auth_tab.no_auth_radio.isChecked()


def test_api_auth_tab_set_values_empty_token_bearer(api_auth_tab: APIAuthTab) -> None:
    """Test setting values with valid bearer auth and token.

    Args:
        api_auth_tab: APIAuthTab instance
    """
    # Validation requires both to be set or both to be None
    settings = APIAuthSettings(auth_type=AuthType.BEARER, auth_token="test-token")

    api_auth_tab.set_values(settings)

    assert api_auth_tab.bearer_auth_radio.isChecked()
    assert api_auth_tab.bearer_token_input.text() == "test-token"
