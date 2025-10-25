"""Tests for memory monitoring middleware."""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from foxhole_stockpiles.api.memory_middleware import MemoryMonitorMiddleware
from foxhole_stockpiles.models.memory_snapshot import MemorySnapshot
from foxhole_stockpiles.services.memory_monitor import MemoryMonitor


@pytest.fixture
def mock_monitor() -> MagicMock:
    """Create a mock MemoryMonitor."""
    monitor = MagicMock(spec=MemoryMonitor)
    monitor.request_count = 0
    monitor.snapshot_interval = 10

    # Mock get_current_memory to return snapshots
    def create_snapshot(rss: float = 100.0) -> MemorySnapshot:
        return MemorySnapshot(
            timestamp=MagicMock(),
            rss_mb=rss,
            vms_mb=200.0,
            percent=5.0,
            available_mb=8192.0,
        )

    monitor.get_current_memory.side_effect = [
        create_snapshot(100.0),  # Before request
        create_snapshot(105.0),  # After request
    ]

    return monitor


@pytest.fixture
def app_with_middleware(mock_monitor: MagicMock) -> FastAPI:
    """Create a FastAPI app with memory monitoring middleware."""
    app = FastAPI()

    app.add_middleware(MemoryMonitorMiddleware, monitor=mock_monitor)

    @app.get("/test")
    async def test_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/memory/stats")
    async def memory_stats() -> dict[str, str]:
        return {"stats": "here"}

    return app


class TestMemoryMonitorMiddleware:
    """Test MemoryMonitorMiddleware."""

    def test_middleware_tracks_normal_requests(
        self, app_with_middleware: FastAPI, mock_monitor: MagicMock
    ) -> None:
        """Test that middleware tracks memory for normal requests."""
        client = TestClient(app_with_middleware)

        response = client.get("/test")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        # Verify monitoring occurred
        assert mock_monitor.get_current_memory.call_count == 2  # Before and after
        assert mock_monitor.record_request.call_count == 1
        assert mock_monitor.request_count == 1

        # Verify record_request was called with correct parameters
        call_args = mock_monitor.record_request.call_args
        assert call_args[1]["path"] == "/test"
        assert call_args[1]["method"] == "GET"
        assert call_args[1]["memory_before_mb"] == 100.0
        assert call_args[1]["memory_after_mb"] == 105.0
        assert call_args[1]["status_code"] == 200
        assert "duration_ms" in call_args[1]

    def test_middleware_skips_memory_endpoints(
        self, app_with_middleware: FastAPI, mock_monitor: MagicMock
    ) -> None:
        """Test that middleware skips /memory/* endpoints."""
        client = TestClient(app_with_middleware)

        response = client.get("/memory/stats")

        assert response.status_code == 200
        assert response.json() == {"stats": "here"}

        # Verify NO monitoring occurred
        mock_monitor.get_current_memory.assert_not_called()
        mock_monitor.record_request.assert_not_called()

    def test_middleware_takes_periodic_snapshots(
        self, app_with_middleware: FastAPI, mock_monitor: MagicMock
    ) -> None:
        """Test that middleware takes snapshots at intervals."""
        client = TestClient(app_with_middleware)

        # Set snapshot interval to 5
        mock_monitor.snapshot_interval = 5
        mock_monitor._take_snapshot = MagicMock()

        # Make 12 requests
        for idx in range(12):
            mock_monitor.request_count = idx + 1
            # Reset side_effect for each request
            mock_monitor.get_current_memory.side_effect = [
                MemorySnapshot(
                    timestamp=MagicMock(),
                    rss_mb=100.0,
                    vms_mb=200.0,
                    percent=5.0,
                    available_mb=8192.0,
                ),
                MemorySnapshot(
                    timestamp=MagicMock(),
                    rss_mb=105.0,
                    vms_mb=200.0,
                    percent=5.0,
                    available_mb=8192.0,
                ),
            ]
            client.get("/test")

        # Should take snapshot at request 5, 10 (2 times)
        assert mock_monitor._take_snapshot.call_count == 2

    def test_middleware_increments_request_count(
        self, app_with_middleware: FastAPI, mock_monitor: MagicMock
    ) -> None:
        """Test that middleware increments request count."""
        client = TestClient(app_with_middleware)

        # Reset request_count
        mock_monitor.request_count = 0

        # Make 3 requests
        for _ in range(3):
            # Reset side_effect for each request
            mock_monitor.get_current_memory.side_effect = [
                MemorySnapshot(
                    timestamp=MagicMock(),
                    rss_mb=100.0,
                    vms_mb=200.0,
                    percent=5.0,
                    available_mb=8192.0,
                ),
                MemorySnapshot(
                    timestamp=MagicMock(),
                    rss_mb=105.0,
                    vms_mb=200.0,
                    percent=5.0,
                    available_mb=8192.0,
                ),
            ]
            client.get("/test")

        assert mock_monitor.request_count == 3

    def test_middleware_calculates_duration(
        self, app_with_middleware: FastAPI, mock_monitor: MagicMock
    ) -> None:
        """Test that middleware calculates request duration."""
        client = TestClient(app_with_middleware)

        client.get("/test")

        call_args = mock_monitor.record_request.call_args
        duration_ms = call_args[1]["duration_ms"]

        # Duration should be positive and reasonable (< 10 seconds for a simple request)
        assert duration_ms > 0
        assert duration_ms < 10000
