"""Tests for ScannerClient."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from foxhole_stockpiles.gui.utils.scanner_client import ScannerClient


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings.

    Returns:
        MagicMock: Mock settings object
    """
    settings = MagicMock()
    settings.api_server.host = "localhost"
    settings.api_server.port = 8000
    settings.api_auth.auth_type = "none"
    settings.api_auth.auth_token = None
    return settings


@pytest.fixture
def client(mock_settings: MagicMock) -> ScannerClient:
    """Create a ScannerClient instance.

    Args:
        mock_settings (MagicMock): Mock settings

    Returns:
        ScannerClient: Client instance
    """
    with patch(
        "foxhole_stockpiles.gui.utils.scanner_client.get_settings", return_value=mock_settings
    ):
        return ScannerClient()


def test_client_initialization(client: ScannerClient) -> None:
    """Test ScannerClient initialization.

    Args:
        client (ScannerClient): Client instance
    """
    assert client.base_url == "http://localhost:8000"
    assert client.auth is None


def test_client_initialization_with_basic_auth(mock_settings: MagicMock) -> None:
    """Test ScannerClient initialization with basic auth.

    Args:
        mock_settings (MagicMock): Mock settings
    """
    mock_settings.api_auth.auth_type = "basic"
    mock_settings.api_auth.auth_token = "user:pass"

    with patch(
        "foxhole_stockpiles.gui.utils.scanner_client.get_settings", return_value=mock_settings
    ):
        client = ScannerClient()

    assert client.auth == ("user", "pass")


def test_scan_screenshot_file_not_found(client: ScannerClient, tmp_path: Path) -> None:
    """Test scan_screenshot with non-existent file.

    Args:
        client (ScannerClient): Client instance
        tmp_path (Path): Temporary directory path
    """
    non_existent = str(tmp_path / "nonexistent.png")
    success, message = client.scan_screenshot(non_existent)

    assert success is False
    assert "File not found" in message


@patch("foxhole_stockpiles.gui.utils.scanner_client.requests.post")
def test_scan_screenshot_success(
    mock_post: MagicMock, client: ScannerClient, tmp_path: Path
) -> None:
    """Test scan_screenshot with successful response.

    Args:
        mock_post (MagicMock): Mock requests.post
        client (ScannerClient): Client instance
        tmp_path (Path): Temporary directory path
    """
    # Create a test file
    test_file = tmp_path / "test.png"
    test_file.write_bytes(b"fake image data")

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "stockpiles": [
            {
                "title": "Test Stockpile",
                "items": [
                    {"code_name": "ItemA", "quantity": 10, "confidence": 0.95, "candidates": []},
                ],
            }
        ]
    }
    mock_post.return_value = mock_response

    success, message = client.scan_screenshot(str(test_file))

    assert success is True
    assert "Test Stockpile" in message
    assert "ItemA" in message
    mock_post.assert_called_once()


@patch("foxhole_stockpiles.gui.utils.scanner_client.requests.post")
def test_scan_screenshot_none_response(
    mock_post: MagicMock, client: ScannerClient, tmp_path: Path
) -> None:
    """Test scan_screenshot with None response.

    Args:
        mock_post (MagicMock): Mock requests.post
        client (ScannerClient): Client instance
        tmp_path (Path): Temporary directory path
    """
    test_file = tmp_path / "test.png"
    test_file.write_bytes(b"fake image data")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = None
    mock_post.return_value = mock_response

    success, message = client.scan_screenshot(str(test_file))

    assert success is True
    assert "Scan completed successfully" in message


@patch("foxhole_stockpiles.gui.utils.scanner_client.requests.post")
def test_scan_screenshot_api_error(
    mock_post: MagicMock, client: ScannerClient, tmp_path: Path
) -> None:
    """Test scan_screenshot with API error.

    Args:
        mock_post (MagicMock): Mock requests.post
        client (ScannerClient): Client instance
        tmp_path (Path): Temporary directory path
    """
    test_file = tmp_path / "test.png"
    test_file.write_bytes(b"fake image data")

    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad request"
    mock_post.return_value = mock_response

    success, message = client.scan_screenshot(str(test_file))

    assert success is False
    assert "API Error (400)" in message


@patch("foxhole_stockpiles.gui.utils.scanner_client.requests.post")
def test_scan_screenshot_connection_error(
    mock_post: MagicMock, client: ScannerClient, tmp_path: Path
) -> None:
    """Test scan_screenshot with connection error.

    Args:
        mock_post (MagicMock): Mock requests.post
        client (ScannerClient): Client instance
        tmp_path (Path): Temporary directory path
    """
    test_file = tmp_path / "test.png"
    test_file.write_bytes(b"fake image data")

    mock_post.side_effect = requests.exceptions.ConnectionError()

    success, message = client.scan_screenshot(str(test_file))

    assert success is False
    assert "Cannot connect to server" in message


def test_format_result_with_stockpiles(client: ScannerClient) -> None:
    """Test _format_result with stockpile data.

    Args:
        client (ScannerClient): Client instance
    """
    result = {
        "stockpiles": [
            {
                "title": "Test Stockpile",
                "items": [
                    {
                        "code_name": "ItemA",
                        "quantity": 10,
                        "confidence": 0.95,
                        "candidates": [
                            {"code_name": "ItemA", "confidence": 0.95},
                            {"code_name": "ItemB", "confidence": 0.85},
                        ],
                    },
                ],
            }
        ]
    }

    formatted = client._format_result(result)

    assert "Test Stockpile" in formatted
    assert "ItemA" in formatted
    assert "10" in formatted
    assert "Alternatives" in formatted
    assert "ItemB" in formatted


def test_format_result_none(client: ScannerClient) -> None:
    """Test _format_result with None.

    Args:
        client (ScannerClient): Client instance
    """
    formatted = client._format_result(None)

    assert "Scan Result" in formatted
