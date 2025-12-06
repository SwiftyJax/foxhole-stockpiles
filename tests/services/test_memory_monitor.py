"""Tests for memory monitor service."""

from unittest.mock import MagicMock, patch

import pytest

from foxhole_stockpiles.models.memory_snapshot import MemorySnapshot
from foxhole_stockpiles.models.request_memory_stats import RequestMemoryStats
from foxhole_stockpiles.services.memory_monitor import MemoryMonitor


class TestMemoryMonitor:
    """Test MemoryMonitor service."""

    @pytest.fixture
    def mock_process(self) -> MagicMock:
        """Create mock psutil.Process."""
        mock = MagicMock()
        mock.memory_info.return_value = MagicMock(rss=1024 * 1024 * 100, vms=1024 * 1024 * 200)
        mock.memory_percent.return_value = 5.0
        return mock

    @pytest.fixture
    def mock_virtual_memory(self) -> MagicMock:
        """Create mock psutil.virtual_memory."""
        mock = MagicMock()
        mock.available = 1024 * 1024 * 1024 * 8  # 8 GB
        return mock

    @pytest.fixture
    def monitor(self, mock_process: MagicMock, mock_virtual_memory: MagicMock) -> MemoryMonitor:
        """Create MemoryMonitor instance with mocked psutil."""
        with (
            patch("foxhole_stockpiles.services.memory_monitor.psutil.Process") as mock_proc_cls,
            patch("foxhole_stockpiles.services.memory_monitor.psutil.virtual_memory") as mock_vm,
        ):
            mock_proc_cls.return_value = mock_process
            mock_vm.return_value = mock_virtual_memory
            return MemoryMonitor(history_size=100, snapshot_interval=10)

    def test_init_creates_initial_snapshot(
        self, mock_process: MagicMock, mock_virtual_memory: MagicMock
    ) -> None:
        """Test that initialization creates an initial snapshot."""
        with (
            patch("foxhole_stockpiles.services.memory_monitor.psutil.Process") as mock_proc_cls,
            patch("foxhole_stockpiles.services.memory_monitor.psutil.virtual_memory") as mock_vm,
        ):
            mock_proc_cls.return_value = mock_process
            mock_vm.return_value = mock_virtual_memory

            monitor = MemoryMonitor(history_size=100, snapshot_interval=10)

            assert len(monitor.history) == 1
            assert monitor.request_count == 0
            assert monitor.snapshot_interval == 10

    def test_get_current_memory(
        self, monitor: MemoryMonitor, mock_process: MagicMock, mock_virtual_memory: MagicMock
    ) -> None:
        """Test getting current memory snapshot."""
        with patch("foxhole_stockpiles.services.memory_monitor.psutil.virtual_memory") as mock_vm:
            mock_vm.return_value = mock_virtual_memory

            snapshot = monitor.get_current_memory()

            assert isinstance(snapshot, MemorySnapshot)
            assert snapshot.rss_mb == 100.0  # 100 MB
            assert snapshot.vms_mb == 200.0  # 200 MB
            assert snapshot.percent == 5.0
            assert snapshot.available_mb == 8192.0  # 8 GB

    def test_take_snapshot_appends_to_history(
        self, monitor: MemoryMonitor, mock_virtual_memory: MagicMock
    ) -> None:
        """Test that _take_snapshot appends to history."""
        initial_count = len(monitor.history)

        with patch("foxhole_stockpiles.services.memory_monitor.psutil.virtual_memory") as mock_vm:
            mock_vm.return_value = mock_virtual_memory

            monitor._take_snapshot()

            assert len(monitor.history) == initial_count + 1

    def test_record_request(self, monitor: MemoryMonitor) -> None:
        """Test recording request statistics."""
        monitor.record_request(
            path="/ocr/scan_image",
            method="POST",
            duration_ms=500.0,
            memory_before_mb=100.0,
            memory_after_mb=105.0,
            status_code=200,
        )

        assert len(monitor.request_stats) == 1
        stats = monitor.request_stats[0]
        assert isinstance(stats, RequestMemoryStats)
        assert stats.path == "/ocr/scan_image"
        assert stats.method == "POST"
        assert stats.duration_ms == 500.0
        assert stats.memory_before_mb == 100.0
        assert stats.memory_after_mb == 105.0
        assert stats.memory_delta_mb == 5.0
        assert stats.status_code == 200

    def test_record_request_logs_warning_for_large_delta(
        self, monitor: MemoryMonitor, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that large memory deltas trigger warning logs."""
        monitor.record_request(
            path="/ocr/scan_image",
            method="POST",
            duration_ms=500.0,
            memory_before_mb=100.0,
            memory_after_mb=115.0,  # 15 MB delta
            status_code=200,
        )

        assert "Significant memory change" in caplog.text
        assert "15.00 MB" in caplog.text

    def test_get_statistics_with_history(
        self, monitor: MemoryMonitor, mock_virtual_memory: MagicMock
    ) -> None:
        """Test getting statistics with history and requests."""
        # Add some request stats
        for i in range(5):
            monitor.record_request(
                path=f"/test/{i}",
                method="GET",
                duration_ms=100.0,
                memory_before_mb=100.0 + i,
                memory_after_mb=100.5 + i,
                status_code=200,
            )

        with patch("foxhole_stockpiles.services.memory_monitor.psutil.virtual_memory") as mock_vm:
            mock_vm.return_value = mock_virtual_memory

            # Add more snapshots
            for _ in range(3):
                monitor._take_snapshot()

            stats = monitor.get_statistics()

            assert "current_memory" in stats
            assert "trends" in stats
            assert "history_stats" in stats
            assert "top_memory_requests" in stats

            # Check current memory
            assert "rss_mb" in stats["current_memory"]
            assert "vms_mb" in stats["current_memory"]
            assert "percent" in stats["current_memory"]
            assert "available_mb" in stats["current_memory"]

            # Check trends
            assert "memory_growth_mb" in stats["trends"]
            assert "time_running_seconds" in stats["trends"]
            assert "growth_rate_mb_per_hour" in stats["trends"]
            assert "total_requests" in stats["trends"]
            assert "avg_memory_delta_per_request_mb" in stats["trends"]

            # Check history stats
            assert "snapshots_count" in stats["history_stats"]
            assert stats["history_stats"]["snapshots_count"] > 1
            assert "min_rss_mb" in stats["history_stats"]
            assert "max_rss_mb" in stats["history_stats"]
            assert "avg_rss_mb" in stats["history_stats"]

            # Check top memory requests
            assert len(stats["top_memory_requests"]) == 5

    def test_get_statistics_no_history(self) -> None:
        """Test getting statistics with no history."""
        with (
            patch("foxhole_stockpiles.services.memory_monitor.psutil.Process"),
            patch("foxhole_stockpiles.services.memory_monitor.psutil.virtual_memory"),
        ):
            monitor = MemoryMonitor(history_size=100, snapshot_interval=10)
            monitor.history.clear()

            stats = monitor.get_statistics()

            assert stats == {"error": "No memory snapshots available"}

    def test_get_statistics_with_many_requests(
        self, monitor: MemoryMonitor, mock_virtual_memory: MagicMock
    ) -> None:
        """Test that statistics correctly calculates average over last 100 requests."""
        # Add 150 requests
        for i in range(150):
            monitor.record_request(
                path=f"/test/{i}",
                method="GET",
                duration_ms=100.0,
                memory_before_mb=100.0,
                memory_after_mb=100.1,  # 0.1 MB delta each
                status_code=200,
            )

        with patch("foxhole_stockpiles.services.memory_monitor.psutil.virtual_memory") as mock_vm:
            mock_vm.return_value = mock_virtual_memory

            stats = monitor.get_statistics()

            # Should only average over last 100 requests
            assert stats["trends"]["avg_memory_delta_per_request_mb"] == 0.1

    def test_force_garbage_collection(
        self, monitor: MemoryMonitor, mock_process: MagicMock, mock_virtual_memory: MagicMock
    ) -> None:
        """Test forcing garbage collection."""
        # Mock force_memory_release to return expected values
        with (
            patch(
                "foxhole_stockpiles.services.memory_monitor.force_memory_release"
            ) as mock_release,
            patch("foxhole_stockpiles.services.memory_monitor.psutil.virtual_memory") as mock_vm,
        ):
            mock_release.return_value = {"gc_collected": 42, "malloc_trimmed": 1}
            mock_vm.return_value = mock_virtual_memory

            # Simulate memory change (first call returns 100MB, second returns 95MB)
            mock_process.memory_info.side_effect = [
                MagicMock(rss=1024 * 1024 * 100, vms=1024 * 1024 * 200),  # Before
                MagicMock(rss=1024 * 1024 * 95, vms=1024 * 1024 * 200),  # After
            ]

            result = monitor.force_garbage_collection()

            assert result["objects_collected"] == 42
            assert result["malloc_trimmed"] == 1
            assert result["memory_before_mb"] == 100.0
            assert result["memory_after_mb"] == 95.0
            assert result["memory_freed_mb"] == 5.0
            mock_release.assert_called_once()

    def test_history_max_size(
        self, mock_process: MagicMock, mock_virtual_memory: MagicMock
    ) -> None:
        """Test that history respects maxlen."""
        with (
            patch("foxhole_stockpiles.services.memory_monitor.psutil.Process") as mock_proc_cls,
            patch("foxhole_stockpiles.services.memory_monitor.psutil.virtual_memory") as mock_vm,
        ):
            mock_proc_cls.return_value = mock_process
            mock_vm.return_value = mock_virtual_memory

            monitor = MemoryMonitor(history_size=5, snapshot_interval=10)

            # Add 10 snapshots
            for _ in range(10):
                monitor._take_snapshot()

            # Should only keep 5 (maxlen)
            assert len(monitor.history) == 5

    def test_request_stats_max_size(self, monitor: MemoryMonitor) -> None:
        """Test that request_stats respects maxlen."""
        # Add 150 requests (history_size is 100)
        for i in range(150):
            monitor.record_request(
                path=f"/test/{i}",
                method="GET",
                duration_ms=100.0,
                memory_before_mb=100.0,
                memory_after_mb=100.5,
                status_code=200,
            )

        # Should only keep 100 (maxlen)
        assert len(monitor.request_stats) == 100

    def test_top_memory_requests_sorted_by_absolute_delta(
        self, monitor: MemoryMonitor, mock_virtual_memory: MagicMock
    ) -> None:
        """Test that top memory requests are sorted by absolute delta."""
        # Add requests with varying deltas (including negative)
        monitor.record_request(
            path="/small",
            method="GET",
            duration_ms=100.0,
            memory_before_mb=100.0,
            memory_after_mb=101.0,
            status_code=200,  # +1 MB
        )
        monitor.record_request(
            path="/large_positive",
            method="GET",
            duration_ms=100.0,
            memory_before_mb=100.0,
            memory_after_mb=120.0,
            status_code=200,  # +20 MB
        )
        monitor.record_request(
            path="/large_negative",
            method="GET",
            duration_ms=100.0,
            memory_before_mb=100.0,
            memory_after_mb=85.0,
            status_code=200,  # -15 MB
        )
        monitor.record_request(
            path="/medium",
            method="GET",
            duration_ms=100.0,
            memory_before_mb=100.0,
            memory_after_mb=110.0,
            status_code=200,  # +10 MB
        )

        with patch("foxhole_stockpiles.services.memory_monitor.psutil.virtual_memory") as mock_vm:
            mock_vm.return_value = mock_virtual_memory

            stats = monitor.get_statistics()

            top_requests = stats["top_memory_requests"]
            assert len(top_requests) == 4

            # Should be sorted by absolute value
            assert top_requests[0]["path"] == "/large_positive"  # 20 MB
            assert top_requests[1]["path"] == "/large_negative"  # 15 MB
            assert top_requests[2]["path"] == "/medium"  # 10 MB
            assert top_requests[3]["path"] == "/small"  # 1 MB
