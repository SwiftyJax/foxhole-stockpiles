"""Tests for APIServerTab."""

import json
from typing import Any

import pytest

from foxhole_stockpiles.core.settings.sections.api import APIServerSettings
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

    settings = api_server_tab.get_values()

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

    settings = api_server_tab.get_values()

    # Should fall back to wildcard
    assert settings.cors_allow_origins == ["*"]


def test_api_server_tab_get_values_empty_cors(api_server_tab: APIServerTab) -> None:
    """Test getting values with empty CORS input.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.cors_input.setPlainText("")

    settings = api_server_tab.get_values()

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

    settings = api_server_tab.get_values()

    # Should preserve whitespace (validation happens in pydantic model)
    assert settings.host == "  192.168.1.1  "


def test_api_server_tab_reload_always_false(api_server_tab: APIServerTab) -> None:
    """Test reload is always False in GUI mode.

    Args:
        api_server_tab: APIServerTab instance
    """
    settings = api_server_tab.get_values()

    assert settings.reload is False


def test_api_server_tab_log_level_always_info(api_server_tab: APIServerTab) -> None:
    """Test log_level is always 'info' (configured in logging tab: Any).

    Args:
        api_server_tab: APIServerTab instance
    """
    settings = api_server_tab.get_values()

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

    settings = api_server_tab.get_values()

    assert settings.workers == 32


def test_api_server_tab_min_workers_boundary(api_server_tab: APIServerTab) -> None:
    """Test workers at minimum boundary.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.workers_input.setValue(1)

    settings = api_server_tab.get_values()

    assert settings.workers == 1


def test_api_server_tab_max_port_boundary(api_server_tab: APIServerTab) -> None:
    """Test port at maximum boundary.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.port_input.setValue(65535)

    settings = api_server_tab.get_values()

    assert settings.port == 65535


def test_api_server_tab_min_port_boundary(api_server_tab: APIServerTab) -> None:
    """Test port at minimum boundary.

    Args:
        api_server_tab: APIServerTab instance
    """
    api_server_tab.port_input.setValue(1)

    settings = api_server_tab.get_values()

    assert settings.port == 1
