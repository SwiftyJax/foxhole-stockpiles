"""Tests for OutputTab."""

from typing import Any
from unittest.mock import patch

import pytest

from foxhole_stockpiles.core.settings.sections.output import (
    FileOutputSettings,
    OutputSettings,
    WebhookOutputSettings,
)
from foxhole_stockpiles.enums.auth_type import AuthType
from foxhole_stockpiles.enums.output_destination import OutputDestination
from foxhole_stockpiles.enums.output_format import OutputFormat
from foxhole_stockpiles.gui.widgets.config_tabs.output_tab import OutputTab


@pytest.fixture
def output_tab(qtbot: Any) -> OutputTab:
    """Create an OutputTab instance.

    Args:
        qtbot: PyQt test fixture

    Returns:
        OutputTab: Tab instance
    """
    tab = OutputTab()
    qtbot.addWidget(tab)
    return tab


def test_output_tab_initialization(output_tab: OutputTab) -> None:
    """Test OutputTab initialization.

    Args:
        output_tab: OutputTab instance
    """
    assert output_tab.format_input is not None
    assert output_tab.destination_input is not None
    assert output_tab.file_group is not None
    assert output_tab.webhook_group is not None
    assert output_tab.file_path_input is not None
    assert output_tab.webhook_url_input is not None
    assert output_tab.webhook_auth_type_input is not None
    assert output_tab.webhook_token_input is not None
    assert output_tab.webhook_client_auth_input is not None


def test_output_tab_destination_options(output_tab: OutputTab) -> None:
    """Test destination combo box has correct options.

    Args:
        output_tab: OutputTab instance
    """
    destinations = [
        output_tab.destination_input.itemText(i)
        for i in range(output_tab.destination_input.count())
    ]
    assert "return" in destinations
    assert "file" in destinations
    assert "webhook" in destinations
    assert "console" in destinations


def test_output_tab_webhook_auth_options(output_tab: OutputTab) -> None:
    """Test webhook auth type combo box has correct options.

    Args:
        output_tab: OutputTab instance
    """
    auth_types = [
        output_tab.webhook_auth_type_input.itemText(i)
        for i in range(output_tab.webhook_auth_type_input.count())
    ]
    assert "null" in auth_types
    assert "basic" in auth_types
    assert "bearer" in auth_types
    assert "forward" in auth_types


def test_output_tab_destination_return_hides_groups(output_tab: OutputTab) -> None:
    """Test return destination hides both groups.

    Args:
        output_tab: OutputTab instance
    """
    output_tab.destination_input.setCurrentText("return")
    output_tab.on_destination_changed()

    assert not output_tab.file_group.isVisible()
    assert not output_tab.webhook_group.isVisible()


def test_output_tab_destination_file_shows_file_group(output_tab: OutputTab) -> None:
    """Test file destination shows file group.

    Args:
        output_tab: OutputTab instance
    """
    output_tab.show()  # Need to show widget for visibility to work
    output_tab.destination_input.setCurrentText("file")
    output_tab.on_destination_changed()

    assert output_tab.file_group.isVisible()
    assert not output_tab.webhook_group.isVisible()


def test_output_tab_destination_webhook_shows_webhook_group(output_tab: OutputTab) -> None:
    """Test webhook destination shows webhook group.

    Args:
        output_tab: OutputTab instance
    """
    output_tab.show()  # Need to show widget for visibility to work
    output_tab.destination_input.setCurrentText("webhook")
    output_tab.on_destination_changed()

    assert not output_tab.file_group.isVisible()
    assert output_tab.webhook_group.isVisible()


def test_output_tab_destination_console_hides_groups(output_tab: OutputTab) -> None:
    """Test console destination hides both groups.

    Args:
        output_tab: OutputTab instance
    """
    output_tab.destination_input.setCurrentText("console")
    output_tab.on_destination_changed()

    assert not output_tab.file_group.isVisible()
    assert not output_tab.webhook_group.isVisible()


def test_output_tab_webhook_auth_null_hides_fields(output_tab: OutputTab) -> None:
    """Test null auth type hides token and client auth fields.

    Args:
        output_tab: OutputTab instance
    """
    output_tab.webhook_auth_type_input.setCurrentText("null")
    output_tab.on_webhook_auth_changed()

    assert not output_tab.auth_token_label.isVisible()
    assert not output_tab.webhook_token_input.isVisible()
    assert not output_tab.client_auth_label.isVisible()
    assert not output_tab.webhook_client_auth_input.isVisible()


def test_output_tab_webhook_auth_basic_shows_token(output_tab: OutputTab) -> None:
    """Test basic auth type shows token field.

    Args:
        output_tab: OutputTab instance
    """
    output_tab.show()  # Need to show widget for visibility to work
    output_tab.webhook_group.show()  # Also show the group
    output_tab.webhook_auth_type_input.setCurrentText("basic")
    output_tab.on_webhook_auth_changed()

    assert output_tab.auth_token_label.isVisible()
    assert output_tab.webhook_token_input.isVisible()
    assert not output_tab.client_auth_label.isVisible()
    assert not output_tab.webhook_client_auth_input.isVisible()


def test_output_tab_webhook_auth_bearer_shows_token(output_tab: OutputTab) -> None:
    """Test bearer auth type shows token field.

    Args:
        output_tab: OutputTab instance
    """
    output_tab.show()  # Need to show widget for visibility to work
    output_tab.webhook_group.show()  # Also show the group
    output_tab.webhook_auth_type_input.setCurrentText("bearer")
    output_tab.on_webhook_auth_changed()

    assert output_tab.auth_token_label.isVisible()
    assert output_tab.webhook_token_input.isVisible()
    assert not output_tab.client_auth_label.isVisible()
    assert not output_tab.webhook_client_auth_input.isVisible()


def test_output_tab_webhook_auth_forward_shows_client_auth(output_tab: OutputTab) -> None:
    """Test forward auth type shows client auth header field.

    Args:
        output_tab: OutputTab instance
    """
    output_tab.show()  # Need to show widget for visibility to work
    output_tab.webhook_group.show()  # Also show the group
    output_tab.webhook_auth_type_input.setCurrentText("forward")
    output_tab.on_webhook_auth_changed()

    assert not output_tab.auth_token_label.isVisible()
    assert not output_tab.webhook_token_input.isVisible()
    assert output_tab.client_auth_label.isVisible()
    assert output_tab.webhook_client_auth_input.isVisible()


def test_output_tab_browse_file(qtbot: Any, output_tab: OutputTab) -> None:
    """Test browse file button.

    Args:
        qtbot: PyQt test fixture
        output_tab: OutputTab instance
    """
    test_path = "/path/to/output.json"

    with patch(
        "foxhole_stockpiles.gui.widgets.config_tabs.output_tab.QFileDialog.getSaveFileName"
    ) as mock_dialog:
        mock_dialog.return_value = (test_path, "JSON Files (*.json)")

        output_tab.browse_file()

        assert output_tab.file_path_input.text() == test_path


def test_output_tab_browse_file_cancel(qtbot: Any, output_tab: OutputTab) -> None:
    """Test browse file cancel.

    Args:
        qtbot: PyQt test fixture
        output_tab: OutputTab instance
    """
    original_text = output_tab.file_path_input.text()

    with patch(
        "foxhole_stockpiles.gui.widgets.config_tabs.output_tab.QFileDialog.getSaveFileName"
    ) as mock_dialog:
        mock_dialog.return_value = ("", "")

        output_tab.browse_file()

        assert output_tab.file_path_input.text() == original_text


def test_output_tab_set_values_file_output(output_tab: OutputTab) -> None:
    """Test setting values with file output.

    Args:
        output_tab: OutputTab instance
    """
    settings = OutputSettings(
        format=OutputFormat.JSON,
        destination=OutputDestination.FILE,
        file=FileOutputSettings(path="/output/data.json"),
    )

    output_tab.set_values(settings)

    assert output_tab.format_input.currentText() == "json"
    assert output_tab.destination_input.currentText() == "file"
    assert output_tab.file_path_input.text() == "/output/data.json"


def test_output_tab_set_values_webhook_basic_auth(output_tab: OutputTab) -> None:
    """Test setting values with webhook basic auth.

    Args:
        output_tab: OutputTab instance
    """
    settings = OutputSettings(
        format=OutputFormat.JSON,
        destination=OutputDestination.WEBHOOK,
        webhook=WebhookOutputSettings(
            url="https://example.com/hook",
            auth_type=AuthType.BASIC,
            token="user:pass",
        ),
    )

    output_tab.set_values(settings)

    assert output_tab.destination_input.currentText() == "webhook"
    assert output_tab.webhook_url_input.text() == "https://example.com/hook"
    assert output_tab.webhook_auth_type_input.currentText() == "basic"
    assert output_tab.webhook_token_input.text() == "user:pass"


def test_output_tab_set_values_webhook_bearer_auth(output_tab: OutputTab) -> None:
    """Test setting values with webhook bearer auth.

    Args:
        output_tab: OutputTab instance
    """
    settings = OutputSettings(
        format=OutputFormat.JSON,
        destination=OutputDestination.WEBHOOK,
        webhook=WebhookOutputSettings(
            url="https://example.com/hook",
            auth_type=AuthType.BEARER,
            token="secret-token",
        ),
    )

    output_tab.set_values(settings)

    assert output_tab.webhook_auth_type_input.currentText() == "bearer"
    assert output_tab.webhook_token_input.text() == "secret-token"


def test_output_tab_set_values_webhook_forward_auth(output_tab: OutputTab) -> None:
    """Test setting values with webhook forward auth.

    Args:
        output_tab: OutputTab instance
    """
    settings = OutputSettings(
        format=OutputFormat.JSON,
        destination=OutputDestination.WEBHOOK,
        webhook=WebhookOutputSettings(
            url="https://example.com/hook",
            auth_type=AuthType.FORWARD,
            client_auth_header="X-Custom-Auth",
        ),
    )

    output_tab.set_values(settings)

    assert output_tab.webhook_auth_type_input.currentText() == "forward"
    assert output_tab.webhook_client_auth_input.text() == "X-Custom-Auth"


def test_output_tab_set_values_webhook_no_auth(output_tab: OutputTab) -> None:
    """Test setting values with webhook no auth.

    Args:
        output_tab: OutputTab instance
    """
    settings = OutputSettings(
        format=OutputFormat.JSON,
        destination=OutputDestination.WEBHOOK,
        webhook=WebhookOutputSettings(
            url="https://example.com/hook",
            auth_type=None,
        ),
    )

    output_tab.set_values(settings)

    assert output_tab.webhook_auth_type_input.currentText() == "null"


def test_output_tab_get_values_file_output(output_tab: OutputTab) -> None:
    """Test getting values with file output.

    Args:
        output_tab: OutputTab instance
    """
    output_tab.format_input.setCurrentText("json")
    output_tab.destination_input.setCurrentText("file")
    output_tab.file_path_input.setText("/test/output.json")

    settings = output_tab.get_values()

    assert settings.format == OutputFormat.JSON
    assert settings.destination == OutputDestination.FILE
    assert settings.file.path == "/test/output.json"


def test_output_tab_get_values_webhook_basic_auth(output_tab: OutputTab) -> None:
    """Test getting values with webhook basic auth.

    Args:
        output_tab: OutputTab instance
    """
    output_tab.destination_input.setCurrentText("webhook")
    output_tab.webhook_url_input.setText("https://test.com/webhook")
    output_tab.webhook_auth_type_input.setCurrentText("basic")
    output_tab.webhook_token_input.setText("testuser:testpass")

    settings = output_tab.get_values()

    assert settings.destination == OutputDestination.WEBHOOK
    assert settings.webhook.url == "https://test.com/webhook"
    assert settings.webhook.auth_type == AuthType.BASIC
    assert settings.webhook.token == "testuser:testpass"


def test_output_tab_get_values_webhook_bearer_auth(output_tab: OutputTab) -> None:
    """Test getting values with webhook bearer auth.

    Args:
        output_tab: OutputTab instance
    """
    output_tab.destination_input.setCurrentText("webhook")
    output_tab.webhook_url_input.setText("https://test.com/webhook")
    output_tab.webhook_auth_type_input.setCurrentText("bearer")
    output_tab.webhook_token_input.setText("my-token")

    settings = output_tab.get_values()

    assert settings.webhook.auth_type == AuthType.BEARER
    assert settings.webhook.token == "my-token"


def test_output_tab_get_values_webhook_forward_auth(output_tab: OutputTab) -> None:
    """Test getting values with webhook forward auth.

    Args:
        output_tab: OutputTab instance
    """
    output_tab.destination_input.setCurrentText("webhook")
    output_tab.webhook_url_input.setText("https://test.com/webhook")
    output_tab.webhook_auth_type_input.setCurrentText("forward")
    output_tab.webhook_client_auth_input.setText("Authorization")

    settings = output_tab.get_values()

    assert settings.webhook.auth_type == AuthType.FORWARD
    assert settings.webhook.client_auth_header == "Authorization"


def test_output_tab_get_values_webhook_no_auth(output_tab: OutputTab) -> None:
    """Test getting values with webhook no auth.

    Args:
        output_tab: OutputTab instance
    """
    output_tab.destination_input.setCurrentText("webhook")
    output_tab.webhook_url_input.setText("https://test.com/webhook")
    output_tab.webhook_auth_type_input.setCurrentText("null")

    settings = output_tab.get_values()

    assert settings.webhook.auth_type is None


def test_output_tab_get_values_console_output(output_tab: OutputTab) -> None:
    """Test getting values with console output.

    Args:
        output_tab: OutputTab instance
    """
    output_tab.destination_input.setCurrentText("console")

    settings = output_tab.get_values()

    assert settings.destination == OutputDestination.CONSOLE


def test_output_tab_get_values_return_output(output_tab: OutputTab) -> None:
    """Test getting values with return output.

    Args:
        output_tab: OutputTab instance
    """
    output_tab.destination_input.setCurrentText("return")

    settings = output_tab.get_values()

    assert settings.destination == OutputDestination.RETURN


def test_output_tab_webhook_token_password_echo_mode(output_tab: OutputTab) -> None:
    """Test webhook token uses password echo mode.

    Args:
        output_tab: OutputTab instance
    """
    from PyQt6.QtWidgets import QLineEdit

    assert output_tab.webhook_token_input.echoMode() == QLineEdit.EchoMode.Password


def test_output_tab_get_values_empty_webhook_url(output_tab: OutputTab) -> None:
    """Test getting values with empty webhook URL when destination is not webhook.

    Args:
        output_tab: OutputTab instance
    """
    # Use console destination instead of webhook to avoid validation error
    # (webhook destination requires url to be set)
    output_tab.destination_input.setCurrentText("console")
    output_tab.webhook_url_input.setText("")

    settings = output_tab.get_values()

    # Webhook settings are still created, but url can be None when not using webhook destination
    assert settings.webhook.url is None
    assert settings.destination == OutputDestination.CONSOLE


def test_output_tab_get_values_empty_webhook_token(output_tab: OutputTab) -> None:
    """Test getting values with empty webhook token when auth is null.

    Args:
        output_tab: OutputTab instance
    """
    # Use null auth to avoid validation error (basic/bearer require token)
    output_tab.destination_input.setCurrentText("webhook")
    output_tab.webhook_url_input.setText("https://example.com/webhook")
    output_tab.webhook_auth_type_input.setCurrentText("null")
    output_tab.webhook_token_input.setText("")

    settings = output_tab.get_values()

    assert settings.webhook.token is None
    assert settings.webhook.auth_type is None


def test_output_tab_get_values_empty_client_auth_header(output_tab: OutputTab) -> None:
    """Test getting values with empty client auth header when auth is null.

    Args:
        output_tab: OutputTab instance
    """
    # Use null auth to avoid validation error (forward requires client_auth_header)
    output_tab.destination_input.setCurrentText("webhook")
    output_tab.webhook_url_input.setText("https://example.com/webhook")
    output_tab.webhook_auth_type_input.setCurrentText("null")
    output_tab.webhook_client_auth_input.setText("")

    settings = output_tab.get_values()

    assert settings.webhook.client_auth_header is None
    assert settings.webhook.auth_type is None


def test_output_tab_set_values_no_file_settings(output_tab: OutputTab) -> None:
    """Test setting values when using console destination.

    Args:
        output_tab: OutputTab instance
    """
    # File settings use default_factory, so they're never None
    # Just test with console destination
    settings = OutputSettings(
        destination=OutputDestination.CONSOLE,
    )

    # Should not raise error
    output_tab.set_values(settings)
    assert output_tab.destination_input.currentText() == "console"


def test_output_tab_set_values_no_webhook_settings(output_tab: OutputTab) -> None:
    """Test setting values when using return destination.

    Args:
        output_tab: OutputTab instance
    """
    # Webhook settings use default_factory, so they're never None
    # Just test with return destination
    settings = OutputSettings(
        destination=OutputDestination.RETURN,
    )

    # Should not raise error
    output_tab.set_values(settings)
    assert output_tab.destination_input.currentText() == "return"
