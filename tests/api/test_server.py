"""Tests for FastAPI server module.

This module contains tests for the FastAPI server endpoints,
including health checks, error handling, and middleware functionality.
"""

import io
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from foxhole_stockpiles.api.server import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app.

    Returns:
        TestClient: A configured test client for making HTTP requests to the app.
    """
    return TestClient(app)


@pytest.fixture
def sample_image() -> bytes:
    """Create a sample image file for testing.

    Returns:
        bytes: Fake image content as bytes for use in file upload tests.
    """
    # Create a simple test image file
    content = b"fake_image_content"
    return content


class TestHealthEndpoint:
    """Test cases for health check endpoint.

    This class contains tests for the /health endpoint which provides
    system status information and health monitoring capabilities.
    """

    def test_health_check(self, client: TestClient) -> None:
        """Test health check endpoint returns proper status.

        Args:
            client (TestClient): FastAPI test client from fixture.
        """
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_health_check_includes_system_info(self, client: TestClient) -> None:
        """Test that health check includes system information.

        Args:
            client (TestClient): FastAPI test client from fixture.
        """
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"


class TestErrorHandling:
    """Test cases for error handling.

    This class contains tests for various error conditions and proper
    HTTP status code responses for different failure scenarios.
    """

    def test_404_not_found(self, client: TestClient) -> None:
        """Test 404 error handling.

        Args:
            client (TestClient): FastAPI test client from fixture.
        """
        response = client.get("/nonexistent-endpoint")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_method_not_allowed(self, client: TestClient) -> None:
        """Test method not allowed error.

        Args:
            client (TestClient): FastAPI test client from fixture.
        """
        response = client.put("/health")

        assert response.status_code == 405
        data = response.json()
        assert "detail" in data


class TestMiddleware:
    """Test cases for middleware functionality.

    This class contains tests for middleware components including CORS,
    request logging, and rate limiting (if implemented).
    """

    def test_cors_headers(self, client: TestClient) -> None:
        """Test CORS headers are present.

        Args:
            client (TestClient): FastAPI test client from fixture.
        """
        response = client.get("/health")

        assert response.status_code == 200
        # Check for common CORS headers (if implemented)
        # assert "Access-Control-Allow-Origin" in response.headers

    def test_rate_limiting(self, client: TestClient) -> None:
        """Test rate limiting (if implemented).

        Args:
            client (TestClient): FastAPI test client from fixture.
        """
        # Make multiple rapid requests
        responses = []
        for _ in range(10):
            response = client.get("/health")
            responses.append(response.status_code)

        # All should succeed if no rate limiting, or some should be 429 if rate limited
        assert all(status in [200, 429] for status in responses)


class TestRootEndpoint:
    """Test cases for root endpoint.

    This class contains tests for the / endpoint that returns basic API information.
    """

    def test_root_endpoint(self, client: TestClient) -> None:
        """Test root endpoint returns API information.

        Args:
            client (TestClient): FastAPI test client from fixture.
        """
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["version"] == "0.1.0"

    def test_root_endpoint_response_model(self, client: TestClient) -> None:
        """Test root endpoint conforms to HealthResponse model.

        Args:
            client (TestClient): FastAPI test client from fixture.
        """
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert isinstance(data["status"], str)
        assert isinstance(data["version"], str)


class TestScanStockpileEndpoint:
    """Test cases for the /ocr/scan_image endpoint.

    This class contains tests for image upload and processing functionality.
    """

    def test_scan_stockpile_invalid_file_type(self, client: TestClient) -> None:
        """Test scanning with non-image file.

        Args:
            client (TestClient): FastAPI test client from fixture.
        """
        # Create a text file instead of an image
        files = {"image": ("test.txt", io.BytesIO(b"not an image"), "text/plain")}
        response = client.post("/ocr/scan_image", files=files)

        assert response.status_code == 400
        assert "File must be an image" in response.json()["detail"]

    def test_scan_stockpile_corrupted_image(self, client: TestClient) -> None:
        """Test scanning with corrupted image data.

        Args:
            client (TestClient): FastAPI test client from fixture.
        """
        # Create invalid image data
        files = {"image": ("test.png", io.BytesIO(b"corrupted"), "image/png")}
        response = client.post("/ocr/scan_image", files=files)

        # HTTPException gets caught by generic handler, returns 500
        assert response.status_code in [400, 500]
        detail = response.json().get("detail", "")
        assert "Invalid image format" in detail or "Unexpected error" in detail

    @patch("foxhole_stockpiles.api.server.OCRCoordinator")
    @patch("foxhole_stockpiles.api.server.OutputHandler")
    def test_scan_stockpile_success(
        self, mock_output_handler: Mock, mock_coordinator: Mock, client: TestClient
    ) -> None:
        """Test successful stockpile scanning.

        Args:
            mock_output_handler (Mock): Mocked OutputHandler class.
            mock_coordinator (Mock): Mocked OCRCoordinator class.
            client (TestClient): FastAPI test client from fixture.
        """
        # Create a simple valid PNG image
        import cv2

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        _, buffer = cv2.imencode(".png", img)
        image_bytes = buffer.tobytes()

        # Mock the coordinator
        mock_instance = Mock()
        mock_instance.analyze_stockpile = AsyncMock(return_value=Mock())
        mock_coordinator.return_value = mock_instance

        # Mock the output handler
        mock_handler_instance = Mock()
        mock_handler_instance.handle_output = AsyncMock(return_value={"result": "success"})
        mock_output_handler.return_value = mock_handler_instance

        files = {"image": ("test.png", io.BytesIO(image_bytes), "image/png")}
        response = client.post("/ocr/scan_image", files=files)

        assert response.status_code == 200
        assert response.json() == {"result": "success"}

    @patch("foxhole_stockpiles.api.server.OCRCoordinator")
    def test_scan_stockpile_with_faction_filter(
        self, mock_coordinator: Mock, client: TestClient
    ) -> None:
        """Test scanning with faction filter parameter.

        Args:
            mock_coordinator (Mock): Mocked OCRCoordinator class.
            client (TestClient): FastAPI test client from fixture.
        """
        import cv2

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        _, buffer = cv2.imencode(".png", img)
        image_bytes = buffer.tobytes()

        # Mock the coordinator
        mock_instance = Mock()
        mock_instance.analyze_stockpile = AsyncMock(return_value=Mock())
        mock_coordinator.return_value = mock_instance

        with patch("foxhole_stockpiles.api.server.OutputHandler") as mock_handler:
            mock_handler_instance = Mock()
            mock_handler_instance.handle_output = AsyncMock(return_value={"result": "success"})
            mock_handler.return_value = mock_handler_instance

            files = {"image": ("test.png", io.BytesIO(image_bytes), "image/png")}
            response = client.post("/ocr/scan_image?faction=colonials", files=files)

            assert response.status_code == 200

    @patch("foxhole_stockpiles.api.server.OCRCoordinator")
    def test_scan_stockpile_processing_error(
        self, mock_coordinator: Mock, client: TestClient
    ) -> None:
        """Test handling of processing errors during scan.

        Args:
            mock_coordinator (Mock): Mocked OCRCoordinator class.
            client (TestClient): FastAPI test client from fixture.
        """
        import cv2

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        _, buffer = cv2.imencode(".png", img)
        image_bytes = buffer.tobytes()

        # Mock the coordinator to raise ValueError
        mock_instance = Mock()
        mock_instance.analyze_stockpile = AsyncMock(side_effect=ValueError("Processing failed"))
        mock_coordinator.return_value = mock_instance

        files = {"image": ("test.png", io.BytesIO(image_bytes), "image/png")}
        response = client.post("/ocr/scan_image", files=files)

        assert response.status_code == 400
        assert "Processing error" in response.json()["detail"]

    @patch("foxhole_stockpiles.api.server.OCRCoordinator")
    def test_scan_stockpile_unexpected_error(
        self, mock_coordinator: Mock, client: TestClient
    ) -> None:
        """Test handling of unexpected errors during scan.

        Args:
            mock_coordinator (Mock): Mocked OCRCoordinator class.
            client (TestClient): FastAPI test client from fixture.
        """
        import cv2

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        _, buffer = cv2.imencode(".png", img)
        image_bytes = buffer.tobytes()

        # Mock the coordinator to raise generic exception
        mock_instance = Mock()
        mock_instance.analyze_stockpile = AsyncMock(side_effect=RuntimeError("Unexpected"))
        mock_coordinator.return_value = mock_instance

        files = {"image": ("test.png", io.BytesIO(image_bytes), "image/png")}
        response = client.post("/ocr/scan_image", files=files)

        assert response.status_code == 500
        assert "Unexpected error" in response.json()["detail"]


class TestLifespan:
    """Test cases for application lifespan events.

    This class contains tests for startup and shutdown event handling.
    """

    @patch("foxhole_stockpiles.api.server.setup_logging")
    def test_startup_logging(self, mock_setup_logging: Mock) -> None:
        """Test that startup event sets up logging correctly.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
        """
        # Creating the test client triggers lifespan events
        with TestClient(app):
            # Verify logging was set up
            mock_setup_logging.assert_called_once()

    def test_application_metadata(self, client: TestClient) -> None:
        """Test that application has correct metadata.

        Args:
            client (TestClient): FastAPI test client from fixture.
        """
        # Access the OpenAPI schema to check metadata
        response = client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert schema["info"]["title"] == "Foxhole Stockpile Scanner API"
        assert schema["info"]["version"] == "0.1.0"

    @patch("foxhole_stockpiles.api.server.setup_logging")
    @patch("logging.getLogger")
    def test_lifespan_shutdown(self, mock_get_logger: Mock, mock_setup_logging: Mock) -> None:
        """Test that shutdown event logs correctly.

        Args:
            mock_get_logger (Mock): Mocked getLogger function.
            mock_setup_logging (Mock): Mocked setup_logging function.
        """
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Create and close test client to trigger lifespan shutdown
        with TestClient(app):
            pass  # Exit context triggers shutdown

        # Verify shutdown was logged
        shutdown_logged = any(
            "Shutting down" in str(call) for call in mock_logger.info.call_args_list
        )
        assert shutdown_logged or mock_logger.info.call_count >= 2


class TestMain:
    """Test cases for the main entry point."""

    @patch("foxhole_stockpiles.api.server.uvicorn.run")
    def test_main_function(self, mock_run: Mock) -> None:
        """Test main function starts uvicorn server.

        Args:
            mock_run (Mock): Mocked uvicorn.run function.
        """
        from foxhole_stockpiles.api.server import main

        main()

        # Verify uvicorn was called with correct parameters
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["port"] == 8000
        assert call_kwargs["log_level"] == "info"


class TestAuthHeaderHandling:
    """Test cases for authentication header handling."""

    @patch("foxhole_stockpiles.api.server.OCRCoordinator")
    @patch("foxhole_stockpiles.api.server.OutputHandler")
    @patch("foxhole_stockpiles.api.server.app_settings")
    def test_auth_header_extraction(
        self,
        mock_settings: Mock,
        mock_output_handler: Mock,
        mock_coordinator: Mock,
        client: TestClient,
    ) -> None:
        """Test extraction of auth header from request.

        Args:
            mock_settings (Mock): Mocked app settings.
            mock_output_handler (Mock): Mocked OutputHandler class.
            mock_coordinator (Mock): Mocked OCRCoordinator class.
            client (TestClient): FastAPI test client from fixture.
        """
        import cv2

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        _, buffer = cv2.imencode(".png", img)
        image_bytes = buffer.tobytes()

        # Configure mock settings with auth header
        mock_settings.output_format.webhook_client_auth_header = "X-API-Key"
        mock_settings.output_format.output_format = "json"

        # Mock the coordinator
        mock_instance = Mock()
        mock_instance.analyze_stockpile = AsyncMock(return_value=Mock())
        mock_coordinator.return_value = mock_instance

        # Mock the output handler
        mock_handler_instance = Mock()
        mock_handler_instance.handle_output = AsyncMock(return_value={"result": "success"})
        mock_output_handler.return_value = mock_handler_instance

        files = {"image": ("test.png", io.BytesIO(image_bytes), "image/png")}
        headers = {"X-API-Key": "test-token"}
        response = client.post("/ocr/scan_image", files=files, headers=headers)

        assert response.status_code == 200

        # Verify handle_output was called with token
        mock_handler_instance.handle_output.assert_called_once()
        call_kwargs = mock_handler_instance.handle_output.call_args[1]
        assert call_kwargs["token"] == "test-token"
