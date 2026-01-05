"""Tests for BasicConfigTab."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from foxhole_stockpiles.core.settings.sections import APIAuthSettings, APIServerSettings
from foxhole_stockpiles.core.settings.sections.output import (
    FileOutputSettings,
    OutputSettings,
    WebhookOutputSettings,
)
from foxhole_stockpiles.core.settings.sections.scanner import ScannerSettings
from foxhole_stockpiles.enums.auth_type import AuthType
from foxhole_stockpiles.enums.output_destination import OutputDestination
from foxhole_stockpiles.gui.widgets.config_tabs.basic_config_tab import BasicConfigTab


@pytest.fixture
def basic_tab(qtbot: Any) -> BasicConfigTab:
    """Create a BasicConfigTab instance.

    Args:
        qtbot: PyQt test fixture

    Returns:
        BasicConfigTab: Tab instance
    """
    tab = BasicConfigTab()
    qtbot.addWidget(tab)
    return tab


def test_basic_tab_initialization(basic_tab: BasicConfigTab) -> None:
    """Test BasicConfigTab initialization.

    Args:
        basic_tab: BasicConfigTab instance
    """
    assert basic_tab.port_input is not None
    assert basic_tab.auth_type_input is not None
    assert basic_tab.username_input is not None
    assert basic_tab.password_input is not None
    assert basic_tab.database_path_input is not None
    assert basic_tab.destination_input is not None
    assert basic_tab.file_path_input is not None
    assert basic_tab.webhook_url_input is not None


def test_basic_tab_default_values(basic_tab: BasicConfigTab) -> None:
    """Test default values are set correctly.

    Args:
        basic_tab: BasicConfigTab instance
    """
    assert basic_tab.port_input.value() == 8000
    assert basic_tab.auth_type_input.currentText() == "None"
    assert basic_tab.destination_input.currentText() == "console"


def test_basic_tab_auth_type_none_hides_credentials(basic_tab: BasicConfigTab) -> None:
    """Test that None auth type hides username/password fields.

    Args:
        basic_tab: BasicConfigTab instance
    """
    basic_tab.auth_type_input.setCurrentText("None")
    basic_tab.on_auth_changed()

    assert not basic_tab.username_label.isVisible()
    assert not basic_tab.username_input.isVisible()
    assert not basic_tab.password_label.isVisible()
    assert not basic_tab.password_input.isVisible()


def test_basic_tab_auth_type_basic_shows_credentials(basic_tab: BasicConfigTab) -> None:
    """Test that Basic auth type shows username/password fields.

    Args:
        basic_tab: BasicConfigTab instance
    """
    basic_tab.show()  # Show widget first
    basic_tab.auth_type_input.setCurrentText("Basic")
    basic_tab.on_auth_changed()

    assert basic_tab.username_label.isVisible()
    assert basic_tab.username_input.isVisible()
    assert basic_tab.password_label.isVisible()
    assert basic_tab.password_input.isVisible()


def test_basic_tab_destination_file_shows_file_group(basic_tab: BasicConfigTab) -> None:
    """Test that file destination shows file group.

    Args:
        basic_tab: BasicConfigTab instance
    """
    basic_tab.show()  # Show widget first
    basic_tab.destination_input.setCurrentText("file")
    basic_tab.on_destination_changed()

    assert basic_tab.file_group.isVisible()
    assert not basic_tab.webhook_group.isVisible()


def test_basic_tab_destination_webhook_shows_webhook_group(basic_tab: BasicConfigTab) -> None:
    """Test that webhook destination shows webhook group.

    Args:
        basic_tab: BasicConfigTab instance
    """
    basic_tab.show()  # Show widget first
    basic_tab.destination_input.setCurrentText("webhook")
    basic_tab.on_destination_changed()

    assert not basic_tab.file_group.isVisible()
    assert basic_tab.webhook_group.isVisible()


def test_basic_tab_destination_console_hides_both_groups(basic_tab: BasicConfigTab) -> None:
    """Test that console destination hides both file and webhook groups.

    Args:
        basic_tab: BasicConfigTab instance
    """
    basic_tab.destination_input.setCurrentText("console")
    basic_tab.on_destination_changed()

    assert not basic_tab.file_group.isVisible()
    assert not basic_tab.webhook_group.isVisible()


def test_basic_tab_destination_return_hides_both_groups(basic_tab: BasicConfigTab) -> None:
    """Test that return destination hides both file and webhook groups.

    Args:
        basic_tab: BasicConfigTab instance
    """
    basic_tab.destination_input.setCurrentText("return")
    basic_tab.on_destination_changed()

    assert not basic_tab.file_group.isVisible()
    assert not basic_tab.webhook_group.isVisible()


def test_basic_tab_webhook_auth_none_hides_credentials(basic_tab: BasicConfigTab) -> None:
    """Test that None webhook auth hides credentials.

    Args:
        basic_tab: BasicConfigTab instance
    """
    basic_tab.webhook_auth_type_input.setCurrentText("None")
    basic_tab.on_webhook_auth_changed()

    assert not basic_tab.webhook_username_label.isVisible()
    assert not basic_tab.webhook_username_input.isVisible()
    assert not basic_tab.webhook_password_label.isVisible()
    assert not basic_tab.webhook_password_input.isVisible()


def test_basic_tab_webhook_auth_basic_shows_credentials(basic_tab: BasicConfigTab) -> None:
    """Test that Basic webhook auth shows credentials.

    Args:
        basic_tab: BasicConfigTab instance
    """
    basic_tab.show()  # Show widget first
    basic_tab.webhook_group.show()  # Also show the group
    basic_tab.webhook_auth_type_input.setCurrentText("Basic")
    basic_tab.on_webhook_auth_changed()

    assert basic_tab.webhook_username_label.isVisible()
    assert basic_tab.webhook_username_input.isVisible()
    assert basic_tab.webhook_password_label.isVisible()
    assert basic_tab.webhook_password_input.isVisible()


def test_basic_tab_browse_database(qtbot: Any, basic_tab: BasicConfigTab) -> None:
    """Test browse database button.

    Args:
        qtbot: PyQt test fixture
        basic_tab: BasicConfigTab instance
    """
    test_path = "/path/to/database.h5"

    with patch(
        "foxhole_stockpiles.gui.widgets.config_tabs.basic_config_tab.QFileDialog.getOpenFileName"
    ) as mock_dialog:
        mock_dialog.return_value = (test_path, "HDF5 Files (*.h5)")

        basic_tab.browse_database()

        assert basic_tab.database_path_input.text() == test_path
        mock_dialog.assert_called_once()


def test_basic_tab_browse_database_cancel(qtbot: Any, basic_tab: BasicConfigTab) -> None:
    """Test browse database cancel.

    Args:
        qtbot: PyQt test fixture
        basic_tab: BasicConfigTab instance
    """
    original_text = basic_tab.database_path_input.text()

    with patch(
        "foxhole_stockpiles.gui.widgets.config_tabs.basic_config_tab.QFileDialog.getOpenFileName"
    ) as mock_dialog:
        mock_dialog.return_value = ("", "")

        basic_tab.browse_database()

        # Should not change text
        assert basic_tab.database_path_input.text() == original_text


def test_basic_tab_browse_file(qtbot: Any, basic_tab: BasicConfigTab) -> None:
    """Test browse file button.

    Args:
        qtbot: PyQt test fixture
        basic_tab: BasicConfigTab instance
    """
    test_path = "/path/to/output.json"

    with patch(
        "foxhole_stockpiles.gui.widgets.config_tabs.basic_config_tab.QFileDialog.getSaveFileName"
    ) as mock_dialog:
        mock_dialog.return_value = (test_path, "JSON Files (*.json)")

        basic_tab.browse_file()

        assert basic_tab.file_path_input.text() == test_path
        mock_dialog.assert_called_once()


def test_basic_tab_browse_file_cancel(qtbot: Any, basic_tab: BasicConfigTab) -> None:
    """Test browse file cancel.

    Args:
        qtbot: PyQt test fixture
        basic_tab: BasicConfigTab instance
    """
    original_text = basic_tab.file_path_input.text()

    with patch(
        "foxhole_stockpiles.gui.widgets.config_tabs.basic_config_tab.QFileDialog.getSaveFileName"
    ) as mock_dialog:
        mock_dialog.return_value = ("", "")

        basic_tab.browse_file()

        # Should not change text
        assert basic_tab.file_path_input.text() == original_text


def test_basic_tab_set_values(basic_tab: BasicConfigTab) -> None:
    """Test setting values from settings objects.

    Args:
        basic_tab: BasicConfigTab instance
    """
    api_server = APIServerSettings(host="192.168.1.1", port=9000)
    api_auth = APIAuthSettings(auth_type=AuthType.BASIC, auth_token="testuser:testpass")
    scanner = ScannerSettings(database_path=Path("/test/db.h5"))
    output = OutputSettings(
        destination=OutputDestination.FILE,
        file=FileOutputSettings(path="output.json"),
    )

    basic_tab.set_values(api_server, api_auth, scanner, output)

    assert basic_tab.port_input.value() == 9000
    assert basic_tab.auth_type_input.currentText() == "Basic"
    assert basic_tab.username_input.text() == "testuser"
    assert basic_tab.password_input.text() == "testpass"
    assert basic_tab.database_path_input.text() == "/test/db.h5"
    assert basic_tab.destination_input.currentText() == "file"
    assert basic_tab.file_path_input.text() == "output.json"


def test_basic_tab_set_values_no_auth(basic_tab: BasicConfigTab) -> None:
    """Test setting values with no authentication.

    Args:
        basic_tab: BasicConfigTab instance
    """
    api_server = APIServerSettings(port=8000)
    api_auth = APIAuthSettings(auth_type=None, auth_token=None)
    scanner = ScannerSettings()
    output = OutputSettings(destination=OutputDestination.CONSOLE)

    basic_tab.set_values(api_server, api_auth, scanner, output)

    assert basic_tab.port_input.value() == 8000
    assert basic_tab.auth_type_input.currentText() == "None"


def test_basic_tab_set_values_webhook_basic_auth(basic_tab: BasicConfigTab) -> None:
    """Test setting values with webhook basic auth.

    Args:
        basic_tab: BasicConfigTab instance
    """
    api_server = APIServerSettings()
    api_auth = APIAuthSettings()
    scanner = ScannerSettings()
    output = OutputSettings(
        destination=OutputDestination.WEBHOOK,
        webhook=WebhookOutputSettings(
            url="https://example.com/webhook",
            auth_type=AuthType.BASIC,
            token="webhookuser:webhookpass",
        ),
    )

    basic_tab.set_values(api_server, api_auth, scanner, output)

    assert basic_tab.destination_input.currentText() == "webhook"
    assert basic_tab.webhook_url_input.text() == "https://example.com/webhook"
    assert basic_tab.webhook_auth_type_input.currentText() == "Basic"
    assert basic_tab.webhook_username_input.text() == "webhookuser"
    assert basic_tab.webhook_password_input.text() == "webhookpass"


def test_basic_tab_set_values_webhook_no_auth(basic_tab: BasicConfigTab) -> None:
    """Test setting values with webhook no auth.

    Args:
        basic_tab: BasicConfigTab instance
    """
    api_server = APIServerSettings()
    api_auth = APIAuthSettings()
    scanner = ScannerSettings()
    output = OutputSettings(
        destination=OutputDestination.WEBHOOK,
        webhook=WebhookOutputSettings(
            url="https://example.com/webhook",
            auth_type=None,
        ),
    )

    basic_tab.set_values(api_server, api_auth, scanner, output)

    assert basic_tab.webhook_auth_type_input.currentText() == "None"


def test_basic_tab_get_values_basic_auth(basic_tab: BasicConfigTab) -> None:
    """Test getting values with basic auth.

    Args:
        basic_tab: BasicConfigTab instance
    """
    basic_tab.port_input.setValue(5000)
    basic_tab.auth_type_input.setCurrentText("Basic")
    basic_tab.username_input.setText("user1")
    basic_tab.password_input.setText("pass1")
    basic_tab.database_path_input.setText("/path/to/db.h5")
    basic_tab.destination_input.setCurrentText("console")

    api_server, api_auth, scanner, output = basic_tab.get_values()

    assert api_server.port == 5000
    assert api_auth.auth_type == AuthType.BASIC
    assert api_auth.auth_token == "user1:pass1"
    assert scanner.database_path == Path("/path/to/db.h5")
    assert output.destination == "console"


def test_basic_tab_get_values_no_auth(basic_tab: BasicConfigTab) -> None:
    """Test getting values with no auth.

    Args:
        basic_tab: BasicConfigTab instance
    """
    basic_tab.port_input.setValue(8000)
    basic_tab.auth_type_input.setCurrentText("None")
    basic_tab.destination_input.setCurrentText("return")

    api_server, api_auth, scanner, output = basic_tab.get_values()

    assert api_server.port == 8000
    assert api_auth.auth_type is None
    assert api_auth.auth_token is None
    assert output.destination == "return"


def test_basic_tab_get_values_file_output(basic_tab: BasicConfigTab) -> None:
    """Test getting values with file output.

    Args:
        basic_tab: BasicConfigTab instance
    """
    basic_tab.destination_input.setCurrentText("file")
    basic_tab.file_path_input.setText("/output/result.json")

    api_server, api_auth, scanner, output = basic_tab.get_values()

    assert output.destination == "file"
    assert output.file.path == "/output/result.json"


def test_basic_tab_get_values_webhook_basic_auth(basic_tab: BasicConfigTab) -> None:
    """Test getting values with webhook basic auth.

    Args:
        basic_tab: BasicConfigTab instance
    """
    basic_tab.destination_input.setCurrentText("webhook")
    basic_tab.webhook_url_input.setText("https://test.com/hook")
    basic_tab.webhook_auth_type_input.setCurrentText("Basic")
    basic_tab.webhook_username_input.setText("hookuser")
    basic_tab.webhook_password_input.setText("hookpass")

    api_server, api_auth, scanner, output = basic_tab.get_values()

    assert output.destination == "webhook"
    assert output.webhook.url == "https://test.com/hook"
    assert output.webhook.auth_type == AuthType.BASIC
    assert output.webhook.token == "hookuser:hookpass"


def test_basic_tab_get_values_webhook_no_auth(basic_tab: BasicConfigTab) -> None:
    """Test getting values with webhook no auth.

    Args:
        basic_tab: BasicConfigTab instance
    """
    basic_tab.destination_input.setCurrentText("webhook")
    basic_tab.webhook_url_input.setText("https://test.com/hook")
    basic_tab.webhook_auth_type_input.setCurrentText("None")

    api_server, api_auth, scanner, output = basic_tab.get_values()

    assert output.webhook.auth_type is None
    assert output.webhook.token is None


def test_basic_tab_get_values_empty_database_path(basic_tab: BasicConfigTab) -> None:
    """Test getting values with empty database path.

    Args:
        basic_tab: BasicConfigTab instance
    """
    basic_tab.database_path_input.setText("")

    api_server, api_auth, scanner, output = basic_tab.get_values()

    assert scanner.database_path is None


def test_basic_tab_get_values_empty_auth_credentials(basic_tab: BasicConfigTab) -> None:
    """Test getting values with empty auth credentials.

    Args:
        basic_tab: BasicConfigTab instance
    """
    basic_tab.auth_type_input.setCurrentText("Basic")
    basic_tab.username_input.setText("")
    basic_tab.password_input.setText("")

    api_server, api_auth, scanner, output = basic_tab.get_values()

    # Empty credentials should return None
    assert api_auth.auth_token is None


def test_basic_tab_password_echo_mode(basic_tab: BasicConfigTab) -> None:
    """Test that password fields use password echo mode.

    Args:
        basic_tab: BasicConfigTab instance
    """
    from PyQt6.QtWidgets import QLineEdit

    assert basic_tab.password_input.echoMode() == QLineEdit.EchoMode.Password
    assert basic_tab.webhook_password_input.echoMode() == QLineEdit.EchoMode.Password


def test_basic_tab_port_range(basic_tab: BasicConfigTab) -> None:
    """Test port input has correct range.

    Args:
        basic_tab: BasicConfigTab instance
    """
    assert basic_tab.port_input.minimum() == 1
    assert basic_tab.port_input.maximum() == 65535


def test_basic_tab_auth_token_without_colon(basic_tab: BasicConfigTab) -> None:
    """Test setting auth token without colon.

    Args:
        basic_tab: BasicConfigTab instance
    """
    api_server = APIServerSettings()
    api_auth = APIAuthSettings(auth_type=AuthType.BASIC, auth_token="invalidtoken")
    scanner = ScannerSettings()
    output = OutputSettings()

    basic_tab.set_values(api_server, api_auth, scanner, output)

    # Should handle gracefully (no colon means no split)
    assert basic_tab.auth_type_input.currentText() == "Basic"


def test_basic_tab_webhook_token_without_colon(basic_tab: BasicConfigTab) -> None:
    """Test setting webhook token without colon.

    Args:
        basic_tab: BasicConfigTab instance
    """
    api_server = APIServerSettings()
    api_auth = APIAuthSettings()
    scanner = ScannerSettings()
    output = OutputSettings(
        destination=OutputDestination.WEBHOOK,
        webhook=WebhookOutputSettings(
            url="https://example.com",
            auth_type=AuthType.BASIC,
            token="invalidtoken",
        ),
    )

    basic_tab.set_values(api_server, api_auth, scanner, output)

    # Should handle gracefully
    assert basic_tab.webhook_auth_type_input.currentText() == "Basic"
