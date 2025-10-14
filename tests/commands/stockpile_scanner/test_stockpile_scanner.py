"""Tests for commands.stockpile_scanner.stockpile_scanner module.

This module contains comprehensive tests for the stockpile scanner command,
including image loading, OCR coordination, and output handling.
"""

import argparse
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pytest

from foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner import (
    get_app_settings,
    main,
)
from foxhole_stockpiles.enums.item_faction import ItemFaction


class TestGetAppSettings:
    """Test suite for get_app_settings function.

    This class contains tests for loading application settings with
    different configurations.
    """

    async def test_get_app_settings_default(self) -> None:
        """Test getting default app settings."""
        settings = get_app_settings(config_file=None)

        assert settings is not None
        assert hasattr(settings, "scanner")
        assert hasattr(settings, "logging")

    async def test_get_app_settings_with_config_file(self, tmp_path: Path) -> None:
        """Test getting app settings from custom config file.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        config_file = tmp_path / "config.json"
        config_file.write_text("{}")

        settings = get_app_settings(config_file=str(config_file))

        assert settings is not None


class TestMainFunction:
    """Test suite for the main CLI function.

    This class contains tests for the main entry point of the stockpile
    scanner command, including argument parsing and workflow execution.
    """

    @pytest.fixture
    def mock_stockpile(self) -> MagicMock:
        """Create a mock stockpile for testing.

        Returns:
            MagicMock: Configured mock Stockpile instance.
        """
        stockpile = MagicMock()
        stockpile.items = []
        stockpile.resolution = "1080"
        stockpile.faction = ItemFaction.NEUTRAL
        return stockpile

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.cv2.imread")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OCRCoordinator")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OutputHandler")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.setup_logging")
    async def test_main_with_basic_args(
        self,
        mock_setup_logging: Mock,
        mock_output_handler_class: Mock,
        mock_coordinator_class: Mock,
        mock_imread: Mock,
        mock_args: Mock,
        mock_stockpile: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with basic arguments.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_output_handler_class (Mock): Mocked OutputHandler class.
            mock_coordinator_class (Mock): Mocked OCRCoordinator class.
            mock_imread (Mock): Mocked cv2.imread function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            mock_stockpile (MagicMock): Mock stockpile from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        # Create test image file
        image_path = tmp_path / "test_screenshot.png"
        image_path.touch()

        database_path = tmp_path / "test.pkl"
        database_path.touch()

        # Mock image loading
        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=None,
            early_exit=0.95,
            faction=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            config=None,
            token=None,
        )

        # Mock OCR coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.analyze_stockpile = AsyncMock(return_value=mock_stockpile)
        mock_coordinator_class.return_value = mock_coordinator

        # Mock output handler
        mock_handler = MagicMock()
        mock_handler.handle_output = AsyncMock(return_value=None)
        mock_output_handler_class.return_value = mock_handler

        await main()

        # Verify image was loaded
        mock_imread.assert_called_once()

        # Verify coordinator was created and analyze was called
        mock_coordinator_class.assert_called_once()
        assert mock_coordinator.analyze_stockpile.call_count > 0

        # Verify output handler was used
        mock_output_handler_class.assert_called_once()
        assert mock_handler.handle_output.call_count > 0

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.cv2.imread")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.setup_logging")
    async def test_main_image_not_found(
        self,
        mock_setup_logging: Mock,
        mock_imread: Mock,
        mock_args: Mock,
        tmp_path: Path,
    ) -> None:
        """Test main function when image file is not found.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_imread (Mock): Mocked cv2.imread function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        image_path = tmp_path / "nonexistent.png"
        database_path = tmp_path / "test.pkl"
        database_path.touch()

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=None,
            early_exit=0.95,
            faction=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            config=None,
            token=None,
        )

        mock_imread.return_value = None

        # Should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.cv2.imread")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OCRCoordinator")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OutputHandler")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.setup_logging")
    async def test_main_with_faction_filter(
        self,
        mock_setup_logging: Mock,
        mock_output_handler_class: Mock,
        mock_coordinator_class: Mock,
        mock_imread: Mock,
        mock_args: Mock,
        mock_stockpile: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with faction filter.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_output_handler_class (Mock): Mocked OutputHandler class.
            mock_coordinator_class (Mock): Mocked OCRCoordinator class.
            mock_imread (Mock): Mocked cv2.imread function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            mock_stockpile (MagicMock): Mock stockpile from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        image_path = tmp_path / "test_screenshot.png"
        image_path.touch()

        database_path = tmp_path / "test.pkl"
        database_path.touch()

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=0.90,
            early_exit=0.95,
            faction="w",
            debug_image=True,
            log_file=None,
            verbose=True,
            quiet=False,
            output_format="json",
            config=None,
            token=None,
        )

        # Mock OCR coordinator
        mock_coordinator = MagicMock()

        async def mock_analyze(*args: Any, **kwargs: Any) -> MagicMock:
            return mock_stockpile

        mock_coordinator.analyze_stockpile = mock_analyze
        mock_coordinator_class.return_value = mock_coordinator

        # Mock output handler
        mock_handler = MagicMock()

        async def mock_handle(*args: Any, **kwargs: Any) -> dict[str, Any]:
            return {"items": []}

        mock_handler.handle_output = mock_handle
        mock_output_handler_class.return_value = mock_handler

        await main()

        # Verify coordinator was configured with faction filter
        mock_coordinator_class.assert_called()
        call_args = mock_coordinator_class.call_args[0][0]
        assert call_args.faction_filter == ItemFaction.WARDENS

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.cv2.imread")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OCRCoordinator")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OutputHandler")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.setup_logging")
    async def test_main_with_custom_confidence(
        self,
        mock_setup_logging: Mock,
        mock_output_handler_class: Mock,
        mock_coordinator_class: Mock,
        mock_imread: Mock,
        mock_args: Mock,
        mock_stockpile: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with custom confidence threshold.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_output_handler_class (Mock): Mocked OutputHandler class.
            mock_coordinator_class (Mock): Mocked OCRCoordinator class.
            mock_imread (Mock): Mocked cv2.imread function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            mock_stockpile (MagicMock): Mock stockpile from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        image_path = tmp_path / "test_screenshot.png"
        image_path.touch()

        database_path = tmp_path / "test.pkl"
        database_path.touch()

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=0.92,
            early_exit=0.95,
            faction=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            config=None,
            token=None,
        )

        # Mock OCR coordinator
        mock_coordinator = MagicMock()

        async def mock_analyze(*args: Any, **kwargs: Any) -> MagicMock:
            return mock_stockpile

        mock_coordinator.analyze_stockpile = mock_analyze
        mock_coordinator_class.return_value = mock_coordinator

        # Mock output handler
        mock_handler = MagicMock()

        async def mock_handle(*args: Any, **kwargs: Any) -> None:
            return None

        mock_handler.handle_output = mock_handle
        mock_output_handler_class.return_value = mock_handler

        await main()

        # Verify coordinator was configured with custom confidence
        mock_coordinator_class.assert_called()
        call_args = mock_coordinator_class.call_args[0][0]
        assert call_args.confidence_threshold == 0.92

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.cv2.imread")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OCRCoordinator")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.setup_logging")
    async def test_main_processing_error(
        self,
        mock_setup_logging: Mock,
        mock_coordinator_class: Mock,
        mock_imread: Mock,
        mock_args: Mock,
        tmp_path: Path,
    ) -> None:
        """Test main function when processing error occurs.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_coordinator_class (Mock): Mocked OCRCoordinator class.
            mock_imread (Mock): Mocked cv2.imread function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        image_path = tmp_path / "test_screenshot.png"
        image_path.touch()

        database_path = tmp_path / "test.pkl"
        database_path.touch()

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=None,
            early_exit=0.95,
            faction=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            config=None,
            token=None,
        )

        # Mock OCR coordinator to raise exception
        mock_coordinator = MagicMock()

        async def mock_analyze(*args: Any, **kwargs: Any) -> None:
            raise ValueError("Processing error")

        mock_coordinator.analyze_stockpile = mock_analyze
        mock_coordinator_class.return_value = mock_coordinator

        # Should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.cv2.imread")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OCRCoordinator")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OutputHandler")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.setup_logging")
    async def test_main_with_quiet_mode(
        self,
        mock_setup_logging: Mock,
        mock_output_handler_class: Mock,
        mock_coordinator_class: Mock,
        mock_imread: Mock,
        mock_args: Mock,
        mock_stockpile: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with quiet mode enabled.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_output_handler_class (Mock): Mocked OutputHandler class.
            mock_coordinator_class (Mock): Mocked OCRCoordinator class.
            mock_imread (Mock): Mocked cv2.imread function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            mock_stockpile (MagicMock): Mock stockpile from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        image_path = tmp_path / "test_screenshot.png"
        image_path.touch()

        database_path = tmp_path / "test.pkl"
        database_path.touch()

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=None,
            early_exit=0.95,
            faction=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=True,  # Quiet mode
            output_format=None,
            config=None,
            token=None,
        )

        # Mock OCR coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.analyze_stockpile = AsyncMock(return_value=mock_stockpile)
        mock_coordinator_class.return_value = mock_coordinator

        # Mock output handler
        mock_handler = MagicMock()
        mock_handler.handle_output = AsyncMock(return_value=None)
        mock_output_handler_class.return_value = mock_handler

        await main()

        # Verify setup_logging was called
        mock_setup_logging.assert_called_once()

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.cv2.imread")
    async def test_main_invalid_confidence(
        self,
        mock_imread: Mock,
        mock_args: Mock,
        tmp_path: Path,
    ) -> None:
        """Test main function with invalid confidence threshold.

        Args:
            mock_imread (Mock): Mocked cv2.imread function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        image_path = tmp_path / "test_screenshot.png"
        image_path.touch()

        database_path = tmp_path / "test.pkl"
        database_path.touch()

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=1.5,  # Invalid: > 1.0
            early_exit=0.95,
            faction=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            config=None,
            token=None,
        )

        # Should exit with code 2 for argparse validation error
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 2

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.cv2.imread")
    async def test_main_image_path_does_not_exist(
        self,
        mock_imread: Mock,
        mock_args: Mock,
        tmp_path: Path,
    ) -> None:
        """Test main function when image path does not exist.

        Args:
            mock_imread (Mock): Mocked cv2.imread function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        image_path = tmp_path / "nonexistent.png"  # Doesn't exist
        database_path = tmp_path / "test.pkl"
        database_path.touch()

        # imread succeeds but Path.exists() returns False
        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=None,
            early_exit=0.95,
            faction=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            config=None,
            token=None,
        )

        # Should exit with code 1 for missing file
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.cv2.imread")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OCRCoordinator")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.setup_logging")
    async def test_main_file_not_found_error(
        self,
        mock_setup_logging: Mock,
        mock_coordinator_class: Mock,
        mock_imread: Mock,
        mock_args: Mock,
        tmp_path: Path,
    ) -> None:
        """Test main function when FileNotFoundError is raised.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_coordinator_class (Mock): Mocked OCRCoordinator class.
            mock_imread (Mock): Mocked cv2.imread function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        image_path = tmp_path / "test_screenshot.png"
        image_path.touch()

        database_path = tmp_path / "test.pkl"
        database_path.touch()

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=None,
            early_exit=0.95,
            faction=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            config=None,
            token=None,
        )

        # Mock OCR coordinator to raise FileNotFoundError
        mock_coordinator = MagicMock()

        async def mock_analyze(*args: Any, **kwargs: Any) -> None:
            raise FileNotFoundError("Database file not found")

        mock_coordinator.analyze_stockpile = mock_analyze
        mock_coordinator_class.return_value = mock_coordinator

        # Should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.cv2.imread")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OCRCoordinator")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.setup_logging")
    async def test_main_generic_exception(
        self,
        mock_setup_logging: Mock,
        mock_coordinator_class: Mock,
        mock_imread: Mock,
        mock_args: Mock,
        tmp_path: Path,
    ) -> None:
        """Test main function when generic Exception is raised.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_coordinator_class (Mock): Mocked OCRCoordinator class.
            mock_imread (Mock): Mocked cv2.imread function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        image_path = tmp_path / "test_screenshot.png"
        image_path.touch()

        database_path = tmp_path / "test.pkl"
        database_path.touch()

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=None,
            early_exit=0.95,
            faction=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            config=None,
            token=None,
        )

        # Mock OCR coordinator to raise generic Exception
        mock_coordinator = MagicMock()

        async def mock_analyze(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("Unexpected runtime error")

        mock_coordinator.analyze_stockpile = mock_analyze
        mock_coordinator_class.return_value = mock_coordinator

        # Should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1
