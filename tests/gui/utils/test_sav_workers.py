"""Tests for SAV worker threads."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QThread

from foxhole_stockpiles.gui.utils.sav_workers import SavMonitorWorker, SavScanWorker
from foxhole_stockpiles.models.stockpile import Stockpile


class TestSavScanWorker:
    """Tests for SavScanWorker."""

    def test_initialization(self) -> None:
        """Test SavScanWorker initialization."""
        sav_path = Path("/test/file.sav")
        output_coordinator = MagicMock()

        worker = SavScanWorker(sav_path, output_coordinator)

        assert worker._sav_path == sav_path
        assert worker._output_coordinator == output_coordinator
        assert isinstance(worker, QThread)

    def test_run_success(self) -> None:
        """Test successful SAV scan."""
        sav_path = Path("/test/file.sav")
        output_coordinator = MagicMock()

        mock_stockpiles = [MagicMock(spec=Stockpile)]

        with (
            patch(
                "foxhole_stockpiles.gui.utils.sav_workers.SaveFileProcessor"
            ) as mock_processor_class,
            patch("foxhole_stockpiles.gui.utils.sav_workers.asyncio.run") as mock_asyncio_run,
        ):
            mock_asyncio_run.return_value = mock_stockpiles

            worker = SavScanWorker(sav_path, output_coordinator)

            # Collect emitted signals
            finished_spy: list[bool] = []
            stockpiles_spy: list[Any] = []
            worker.finished.connect(lambda success: finished_spy.append(success))
            worker.stockpiles_found.connect(lambda s: stockpiles_spy.append(s))

            # Run the worker directly (not in thread for testing)
            worker.run()

            # Verify processor was created with correct arguments
            mock_processor_class.assert_called_once_with(
                file_path=sav_path,
                output_coordinator=output_coordinator,
                emit_all_on_start=True,
            )

            # Verify asyncio.run was called
            mock_asyncio_run.assert_called_once()

            # Verify signals
            assert len(stockpiles_spy) == 1
            assert stockpiles_spy[0] == mock_stockpiles
            assert len(finished_spy) == 1
            assert finished_spy[0] is True

    def test_run_runtime_error(self) -> None:
        """Test SAV scan with runtime error."""
        sav_path = Path("/nonexistent/file.sav")
        output_coordinator = MagicMock()

        with patch(
            "foxhole_stockpiles.gui.utils.sav_workers.SaveFileProcessor",
            side_effect=RuntimeError("Parse failed"),
        ):
            worker = SavScanWorker(sav_path, output_coordinator)

            error_spy: list[str] = []
            finished_spy: list[bool] = []
            worker.error.connect(lambda msg: error_spy.append(msg))
            worker.finished.connect(lambda success: finished_spy.append(success))

            worker.run()

            assert len(error_spy) == 1
            assert "Parse failed" in error_spy[0]
            assert len(finished_spy) == 1
            assert finished_spy[0] is False

    def test_run_generic_exception(self) -> None:
        """Test SAV scan with generic exception."""
        sav_path = Path("/test/file.sav")
        output_coordinator = MagicMock()

        with patch(
            "foxhole_stockpiles.gui.utils.sav_workers.SaveFileProcessor",
            side_effect=ValueError("Unexpected error"),
        ):
            worker = SavScanWorker(sav_path, output_coordinator)

            error_spy: list[str] = []
            finished_spy: list[bool] = []
            worker.error.connect(lambda msg: error_spy.append(msg))
            worker.finished.connect(lambda success: finished_spy.append(success))

            worker.run()

            assert len(error_spy) == 1
            assert "Error processing SAV file" in error_spy[0]
            assert "Unexpected error" in error_spy[0]
            assert len(finished_spy) == 1
            assert finished_spy[0] is False


class TestSavMonitorWorker:
    """Tests for SavMonitorWorker."""

    def test_initialization(self) -> None:
        """Test SavMonitorWorker initialization."""
        sav_path = Path("/test/file.sav")
        output_coordinator = MagicMock()
        poll_interval = 2.5

        worker = SavMonitorWorker(sav_path, output_coordinator, poll_interval)

        assert worker._sav_path == sav_path
        assert worker._output_coordinator == output_coordinator
        assert worker._poll_interval == poll_interval
        assert worker._should_stop is False
        assert worker._processor is None
        assert isinstance(worker, QThread)

    def test_initialization_default_poll_interval(self) -> None:
        """Test SavMonitorWorker initialization with default poll interval."""
        sav_path = Path("/test/file.sav")
        output_coordinator = MagicMock()

        worker = SavMonitorWorker(sav_path, output_coordinator)

        assert worker._poll_interval == 1.0

    def test_stop(self) -> None:
        """Test stopping the monitor worker."""
        sav_path = Path("/test/file.sav")
        output_coordinator = MagicMock()

        worker = SavMonitorWorker(sav_path, output_coordinator)
        mock_processor = MagicMock()
        worker._processor = mock_processor

        worker.stop()

        assert worker._should_stop is True
        mock_processor.stop.assert_called_once()

    def test_stop_no_processor(self) -> None:
        """Test stopping the monitor worker when no processor exists."""
        sav_path = Path("/test/file.sav")
        output_coordinator = MagicMock()

        worker = SavMonitorWorker(sav_path, output_coordinator)

        # Should not raise
        worker.stop()

        assert worker._should_stop is True

    def test_run_runtime_error(self) -> None:
        """Test monitor run with runtime error."""
        sav_path = Path("/nonexistent/file.sav")
        output_coordinator = MagicMock()

        with patch(
            "foxhole_stockpiles.gui.utils.sav_workers.SaveFileProcessor",
            side_effect=RuntimeError("Processor init failed"),
        ):
            worker = SavMonitorWorker(sav_path, output_coordinator)

            error_spy: list[str] = []
            finished_spy: list[bool] = []
            worker.error.connect(lambda msg: error_spy.append(msg))
            worker.finished.connect(lambda success: finished_spy.append(success))

            worker.run()

            assert len(error_spy) == 1
            assert "Processor init failed" in error_spy[0]
            assert len(finished_spy) == 1
            assert finished_spy[0] is False

    def test_run_generic_exception(self) -> None:
        """Test monitor run with generic exception."""
        sav_path = Path("/test/file.sav")
        output_coordinator = MagicMock()

        with patch(
            "foxhole_stockpiles.gui.utils.sav_workers.SaveFileProcessor",
            side_effect=ValueError("Init error"),
        ):
            worker = SavMonitorWorker(sav_path, output_coordinator)

            error_spy: list[str] = []
            finished_spy: list[bool] = []
            worker.error.connect(lambda msg: error_spy.append(msg))
            worker.finished.connect(lambda success: finished_spy.append(success))

            worker.run()

            assert len(error_spy) == 1
            assert "Error monitoring SAV file" in error_spy[0]
            assert "Init error" in error_spy[0]
            assert len(finished_spy) == 1
            assert finished_spy[0] is False

    def test_run_success(self) -> None:
        """Test successful monitor run."""
        sav_path = Path("/test/file.sav")
        output_coordinator = MagicMock()

        with (
            patch(
                "foxhole_stockpiles.gui.utils.sav_workers.SaveFileProcessor"
            ) as mock_processor_class,
            patch("foxhole_stockpiles.gui.utils.sav_workers.asyncio.run") as mock_asyncio_run,
        ):
            worker = SavMonitorWorker(sav_path, output_coordinator)

            finished_spy: list[bool] = []
            worker.finished.connect(lambda success: finished_spy.append(success))

            worker.run()

            # Verify processor was created with correct arguments
            mock_processor_class.assert_called_once_with(
                file_path=sav_path,
                output_coordinator=output_coordinator,
                poll_interval=1.0,
                emit_all_on_start=False,
            )

            # Verify asyncio.run was called with _run_monitor coroutine
            mock_asyncio_run.assert_called_once()

            # Verify signals
            assert len(finished_spy) == 1
            assert finished_spy[0] is True
