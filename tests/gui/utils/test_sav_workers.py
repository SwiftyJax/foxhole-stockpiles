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
        uesave_path = Path("/test/uesave")
        output_coordinator = MagicMock()

        worker = SavScanWorker(sav_path, uesave_path, output_coordinator)

        assert worker._sav_path == sav_path
        assert worker._uesave_path == uesave_path
        assert worker._output_coordinator == output_coordinator
        assert isinstance(worker, QThread)

    def test_initialization_none_uesave(self) -> None:
        """Test SavScanWorker initialization with None uesave path."""
        sav_path = Path("/test/file.sav")
        output_coordinator = MagicMock()

        worker = SavScanWorker(sav_path, None, output_coordinator)

        assert worker._sav_path == sav_path
        assert worker._uesave_path is None
        assert worker._output_coordinator == output_coordinator

    def test_run_success(self) -> None:
        """Test successful SAV scan."""
        sav_path = Path("/test/file.sav")
        uesave_path = Path("/test/uesave")
        output_coordinator = MagicMock()

        mock_stockpiles = [MagicMock(spec=Stockpile)]

        with (
            patch(
                "foxhole_stockpiles.gui.utils.sav_workers.SaveFileConverter"
            ) as mock_converter_class,
            patch(
                "foxhole_stockpiles.gui.utils.sav_workers.SaveFileProcessor"
            ) as mock_processor_class,
            patch("foxhole_stockpiles.gui.utils.sav_workers.asyncio.run") as mock_asyncio_run,
        ):
            mock_asyncio_run.return_value = mock_stockpiles

            worker = SavScanWorker(sav_path, uesave_path, output_coordinator)

            # Collect emitted signals
            finished_spy: list[bool] = []
            stockpiles_spy: list[Any] = []
            worker.finished.connect(lambda success: finished_spy.append(success))
            worker.stockpiles_found.connect(lambda s: stockpiles_spy.append(s))

            # Run the worker directly (not in thread for testing)
            worker.run()

            # Verify converter was created
            mock_converter_class.assert_called_once_with(uesave_path=uesave_path)

            # Verify processor was created
            mock_processor_class.assert_called_once()

            # Verify asyncio.run was called
            mock_asyncio_run.assert_called_once()

            # Verify signals
            assert len(stockpiles_spy) == 1
            assert stockpiles_spy[0] == mock_stockpiles
            assert len(finished_spy) == 1
            assert finished_spy[0] is True

    def test_run_file_not_found(self) -> None:
        """Test SAV scan with file not found error."""
        sav_path = Path("/nonexistent/file.sav")
        output_coordinator = MagicMock()

        with patch(
            "foxhole_stockpiles.gui.utils.sav_workers.SaveFileConverter",
            side_effect=FileNotFoundError("File not found"),
        ):
            worker = SavScanWorker(sav_path, None, output_coordinator)

            error_spy: list[str] = []
            finished_spy: list[bool] = []
            worker.error.connect(lambda msg: error_spy.append(msg))
            worker.finished.connect(lambda success: finished_spy.append(success))

            worker.run()

            assert len(error_spy) == 1
            assert "File not found" in error_spy[0]
            assert len(finished_spy) == 1
            assert finished_spy[0] is False

    def test_run_generic_exception(self) -> None:
        """Test SAV scan with generic exception."""
        sav_path = Path("/test/file.sav")
        output_coordinator = MagicMock()

        with patch(
            "foxhole_stockpiles.gui.utils.sav_workers.SaveFileConverter",
            side_effect=RuntimeError("Unexpected error"),
        ):
            worker = SavScanWorker(sav_path, None, output_coordinator)

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
        uesave_path = Path("/test/uesave")
        output_coordinator = MagicMock()
        poll_interval = 2.5

        worker = SavMonitorWorker(sav_path, uesave_path, output_coordinator, poll_interval)

        assert worker._sav_path == sav_path
        assert worker._uesave_path == uesave_path
        assert worker._output_coordinator == output_coordinator
        assert worker._poll_interval == poll_interval
        assert worker._should_stop is False
        assert worker._processor is None
        assert isinstance(worker, QThread)

    def test_initialization_default_poll_interval(self) -> None:
        """Test SavMonitorWorker initialization with default poll interval."""
        sav_path = Path("/test/file.sav")
        output_coordinator = MagicMock()

        worker = SavMonitorWorker(sav_path, None, output_coordinator)

        assert worker._poll_interval == 1.0

    def test_stop(self) -> None:
        """Test stopping the monitor worker."""
        sav_path = Path("/test/file.sav")
        output_coordinator = MagicMock()

        worker = SavMonitorWorker(sav_path, None, output_coordinator)
        mock_processor = MagicMock()
        worker._processor = mock_processor

        worker.stop()

        assert worker._should_stop is True
        mock_processor.stop.assert_called_once()

    def test_stop_no_processor(self) -> None:
        """Test stopping the monitor worker when no processor exists."""
        sav_path = Path("/test/file.sav")
        output_coordinator = MagicMock()

        worker = SavMonitorWorker(sav_path, None, output_coordinator)

        # Should not raise
        worker.stop()

        assert worker._should_stop is True

    def test_run_file_not_found(self) -> None:
        """Test monitor run with file not found error."""
        sav_path = Path("/nonexistent/file.sav")
        output_coordinator = MagicMock()

        with patch(
            "foxhole_stockpiles.gui.utils.sav_workers.SaveFileConverter",
            side_effect=FileNotFoundError("uesave not found"),
        ):
            worker = SavMonitorWorker(sav_path, None, output_coordinator)

            error_spy: list[str] = []
            finished_spy: list[bool] = []
            worker.error.connect(lambda msg: error_spy.append(msg))
            worker.finished.connect(lambda success: finished_spy.append(success))

            worker.run()

            assert len(error_spy) == 1
            assert "uesave not found" in error_spy[0]
            assert len(finished_spy) == 1
            assert finished_spy[0] is False

    def test_run_generic_exception(self) -> None:
        """Test monitor run with generic exception."""
        sav_path = Path("/test/file.sav")
        output_coordinator = MagicMock()

        with patch(
            "foxhole_stockpiles.gui.utils.sav_workers.SaveFileConverter",
            side_effect=RuntimeError("Init error"),
        ):
            worker = SavMonitorWorker(sav_path, None, output_coordinator)

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
                "foxhole_stockpiles.gui.utils.sav_workers.SaveFileConverter"
            ) as mock_converter_class,
            patch(
                "foxhole_stockpiles.gui.utils.sav_workers.SaveFileProcessor"
            ) as mock_processor_class,
            patch("foxhole_stockpiles.gui.utils.sav_workers.asyncio.run") as mock_asyncio_run,
        ):
            worker = SavMonitorWorker(sav_path, None, output_coordinator)

            finished_spy: list[bool] = []
            worker.finished.connect(lambda success: finished_spy.append(success))

            worker.run()

            # Verify converter was created
            mock_converter_class.assert_called_once()

            # Verify processor was created
            mock_processor_class.assert_called_once()

            # Verify asyncio.run was called with _run_monitor coroutine
            mock_asyncio_run.assert_called_once()

            # Verify signals
            assert len(finished_spy) == 1
            assert finished_spy[0] is True
