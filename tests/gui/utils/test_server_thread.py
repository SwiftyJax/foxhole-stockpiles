"""Tests for ServerThread."""

from unittest.mock import MagicMock, patch

import pytest

from foxhole_stockpiles.gui.utils.server_thread import ServerThread


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings.

    Returns:
        MagicMock: Mock settings object
    """
    settings = MagicMock()
    settings.api_server.host = "127.0.0.1"
    settings.api_server.port = 8000
    settings.api_server.log_level = "info"
    return settings


def test_server_thread_initialization() -> None:
    """Test ServerThread initialization."""
    thread = ServerThread()

    assert thread.server is None
    assert thread.daemon is True
    assert thread._stop_event is not None


@patch("foxhole_stockpiles.gui.utils.server_thread.uvicorn.Server")
@patch("foxhole_stockpiles.gui.utils.server_thread.uvicorn.Config")
@patch("foxhole_stockpiles.gui.utils.server_thread.get_settings")
def test_server_thread_run(
    mock_get_settings: MagicMock,
    mock_config: MagicMock,
    mock_server_class: MagicMock,
    mock_settings: MagicMock,
) -> None:
    """Test ServerThread run method.

    Args:
        mock_get_settings (MagicMock): Mock get_settings function
        mock_config (MagicMock): Mock uvicorn.Config
        mock_server_class (MagicMock): Mock uvicorn.Server class
        mock_settings (MagicMock): Mock settings
    """
    mock_get_settings.return_value = mock_settings

    mock_server_instance = MagicMock()
    mock_server_class.return_value = mock_server_instance

    thread = ServerThread()
    thread.run()

    # Verify config was created with correct parameters
    mock_config.assert_called_once_with(
        "foxhole_stockpiles.api.server:app",
        host="127.0.0.1",
        port=8000,
        workers=1,
        reload=False,
        log_level="info",
    )

    # Verify server was created and run
    mock_server_class.assert_called_once()
    mock_server_instance.run.assert_called_once()


@patch("foxhole_stockpiles.gui.utils.server_thread.uvicorn.Server")
@patch("foxhole_stockpiles.gui.utils.server_thread.uvicorn.Config")
@patch("foxhole_stockpiles.gui.utils.server_thread.get_settings")
def test_server_thread_stop(
    mock_get_settings: MagicMock,
    mock_config: MagicMock,
    mock_server_class: MagicMock,
    mock_settings: MagicMock,
) -> None:
    """Test ServerThread stop method.

    Args:
        mock_get_settings (MagicMock): Mock get_settings function
        mock_config (MagicMock): Mock uvicorn.Config
        mock_server_class (MagicMock): Mock uvicorn.Server class
        mock_settings (MagicMock): Mock settings
    """
    mock_get_settings.return_value = mock_settings

    mock_server_instance = MagicMock()
    mock_server_class.return_value = mock_server_instance

    thread = ServerThread()
    thread.server = mock_server_instance

    thread.stop()

    assert mock_server_instance.should_exit is True
    assert thread._stop_event.is_set() is True


@patch("foxhole_stockpiles.gui.utils.server_thread.uvicorn.Server")
@patch("foxhole_stockpiles.gui.utils.server_thread.uvicorn.Config")
@patch("foxhole_stockpiles.gui.utils.server_thread.get_settings")
@patch("foxhole_stockpiles.gui.utils.server_thread.logger")
def test_server_thread_run_exception(
    mock_logger: MagicMock,
    mock_get_settings: MagicMock,
    mock_config: MagicMock,
    mock_server_class: MagicMock,
    mock_settings: MagicMock,
) -> None:
    """Test ServerThread handles exceptions during run.

    Args:
        mock_logger (MagicMock): Mock logger
        mock_get_settings (MagicMock): Mock get_settings function
        mock_config (MagicMock): Mock uvicorn.Config
        mock_server_class (MagicMock): Mock uvicorn.Server class
        mock_settings (MagicMock): Mock settings
    """
    mock_get_settings.return_value = mock_settings

    mock_server_instance = MagicMock()
    mock_server_instance.run.side_effect = Exception("Server error")
    mock_server_class.return_value = mock_server_instance

    thread = ServerThread()
    thread.run()

    # Verify error was logged
    mock_logger.error.assert_called()
