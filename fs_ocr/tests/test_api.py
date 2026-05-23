"""Tests for fs_ocr public API.

This module tests the public OCRScanner API without requiring
actual image scanning (mocked coordinator).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fs_ocr import (
    SCHEMA_VERSION,
    OCRScanner,
    ScannerConfig,
    ScannerInfo,
    Stockpile,
    StockpileItem,
)


class TestScannerConfig:
    """Test suite for ScannerConfig."""

    def test_create_with_defaults(self, tmp_path: Path) -> None:
        """Test creating config with default values."""
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerConfig(database_path=db_path)

        assert config.database_path == db_path
        assert config.tessdata_path == "tessdata"
        assert config.custom_model == "renner_numbers"
        assert config.template_cache_size == 16
        assert config.early_exit_threshold == 0.0

    def test_create_with_custom_values(self, tmp_path: Path) -> None:
        """Test creating config with custom values."""
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerConfig(
            database_path=db_path,
            tessdata_path="/custom/tessdata",
            early_exit_threshold=0.9,
            template_cache_size=100,
        )

        assert config.tessdata_path == "/custom/tessdata"
        assert config.early_exit_threshold == 0.9
        assert config.template_cache_size == 100


class TestOCRScannerInitialization:
    """Test suite for OCRScanner initialization."""

    def test_init_raises_on_missing_database(self, tmp_path: Path) -> None:
        """Test that init raises FileNotFoundError for missing database."""
        config = ScannerConfig(database_path=tmp_path / "nonexistent.h5")

        with pytest.raises(FileNotFoundError, match="Database not found"):
            OCRScanner(config)

    @patch("fs_ocr._impl.coordinator.OCRCoordinator")
    def test_init_success(self, mock_coordinator: MagicMock, tmp_path: Path) -> None:
        """Test successful scanner initialization."""
        db_path = tmp_path / "test.h5"
        db_path.touch()
        config = ScannerConfig(database_path=db_path)

        scanner = OCRScanner(config)

        assert scanner._config == config
        assert not scanner._closed
        mock_coordinator.assert_called_once()


class TestOCRScannerContextManager:
    """Test suite for OCRScanner context manager."""

    @patch("fs_ocr._impl.coordinator.OCRCoordinator")
    def test_context_manager_closes_on_exit(
        self, mock_coordinator: MagicMock, tmp_path: Path
    ) -> None:
        """Test that context manager closes scanner on exit."""
        db_path = tmp_path / "test.h5"
        db_path.touch()
        config = ScannerConfig(database_path=db_path)

        with OCRScanner(config) as scanner:
            assert not scanner._closed

        assert scanner._closed


class TestOCRScannerScan:
    """Test suite for OCRScanner.scan method."""

    @patch("fs_ocr._impl.coordinator.OCRCoordinator")
    async def test_scan_raises_when_closed(
        self, mock_coordinator: MagicMock, tmp_path: Path
    ) -> None:
        """Test that scan raises RuntimeError when scanner is closed."""
        db_path = tmp_path / "test.h5"
        db_path.touch()
        config = ScannerConfig(database_path=db_path)

        scanner = OCRScanner(config)
        scanner.close()

        with pytest.raises(RuntimeError, match="Scanner has been closed"):
            await scanner.scan(b"fake image data")


class TestOCRScannerInfo:
    """Test suite for OCRScanner.info method."""

    @patch("fs_ocr._impl.coordinator.OCRCoordinator")
    def test_info_returns_scanner_info(self, mock_coordinator: MagicMock, tmp_path: Path) -> None:
        """Test that info returns valid ScannerInfo."""
        db_path = tmp_path / "test.h5"
        db_path.touch()
        config = ScannerConfig(database_path=db_path)

        with OCRScanner(config) as scanner:
            info = scanner.info()

        assert isinstance(info, ScannerInfo)
        assert info.schema_version == "1"
        assert info.implementation == "python"
        assert info.version is not None


class TestPublicExports:
    """Test suite for public API exports."""

    def test_schema_version(self) -> None:
        """Test SCHEMA_VERSION is exported."""
        assert SCHEMA_VERSION == "1"

    def test_stockpile_export(self) -> None:
        """Test Stockpile is exported from fs_ocr."""
        # Should be able to create a Stockpile instance
        stockpile = Stockpile()
        assert stockpile.name == ""
        assert stockpile.items == []

    def test_stockpile_item_export(self) -> None:
        """Test StockpileItem is exported from fs_ocr."""
        item = StockpileItem(code="TestItem", quantity=5)
        assert item.code == "TestItem"
        assert item.quantity == 5
