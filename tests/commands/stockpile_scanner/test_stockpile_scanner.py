"""Tests for commands.stockpile_scanner.stockpile_scanner module.

This module contains comprehensive tests for the stockpile scanner command,
including image loading, OCR coordination, and output handling.
"""

import argparse
import sys
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
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OutputCoordinator")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.setup_logging")
    async def test_main_with_basic_args(
        self,
        mock_setup_logging: Mock,
        mock_output_coordinator_class: Mock,
        mock_coordinator_class: Mock,
        mock_imread: Mock,
        mock_args: Mock,
        mock_stockpile: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with basic arguments.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_output_coordinator_class (Mock): Mocked OutputCoordinator class.
            mock_coordinator_class (Mock): Mocked OCRCoordinator class.
            mock_imread (Mock): Mocked cv2.imread function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            mock_stockpile (MagicMock): Mock stockpile from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        # Create test image file
        image_path = tmp_path / "test_screenshot.png"
        image_path.touch()

        database_path = tmp_path / "test.h5"
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
            language=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            output_destination=None,
            output_file=None,
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
        mock_output_coordinator_class.return_value = mock_handler

        await main()

        # Verify image was loaded
        mock_imread.assert_called_once()

        # Verify coordinator was created and analyze was called
        mock_coordinator_class.assert_called_once()
        assert mock_coordinator.analyze_stockpile.call_count > 0

        # Verify output handler was used
        mock_output_coordinator_class.assert_called_once()
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
        database_path = tmp_path / "test.h5"
        database_path.touch()

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=None,
            early_exit=0.95,
            faction=None,
            language=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            output_destination=None,
            output_file=None,
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
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OutputCoordinator")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.setup_logging")
    async def test_main_with_faction_filter(
        self,
        mock_setup_logging: Mock,
        mock_output_coordinator_class: Mock,
        mock_coordinator_class: Mock,
        mock_imread: Mock,
        mock_args: Mock,
        mock_stockpile: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with faction filter.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_output_coordinator_class (Mock): Mocked OutputCoordinator class.
            mock_coordinator_class (Mock): Mocked OCRCoordinator class.
            mock_imread (Mock): Mocked cv2.imread function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            mock_stockpile (MagicMock): Mock stockpile from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        image_path = tmp_path / "test_screenshot.png"
        image_path.touch()

        database_path = tmp_path / "test.h5"
        database_path.touch()

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=0.90,
            early_exit=0.95,
            faction="w",
            language=None,
            debug_image=True,
            log_file=None,
            verbose=True,
            quiet=False,
            output_format="json",
            output_destination=None,
            output_file=None,
            config=None,
            token=None,
        )

        # Mock OCR coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.analyze_stockpile = AsyncMock(return_value=mock_stockpile)
        mock_coordinator_class.return_value = mock_coordinator

        # Mock output handler
        mock_handler = MagicMock()
        mock_handler.handle_output = AsyncMock(return_value={"items": []})
        mock_output_coordinator_class.return_value = mock_handler

        await main()

        # Verify analyze_stockpile was called with faction parameter
        mock_coordinator.analyze_stockpile.assert_called_once()
        call_kwargs = mock_coordinator.analyze_stockpile.call_args[1]
        assert call_kwargs["faction"] == ItemFaction.WARDENS

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.cv2.imread")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OCRCoordinator")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OutputCoordinator")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.setup_logging")
    async def test_main_with_custom_confidence(
        self,
        mock_setup_logging: Mock,
        mock_output_coordinator_class: Mock,
        mock_coordinator_class: Mock,
        mock_imread: Mock,
        mock_args: Mock,
        mock_stockpile: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with custom confidence threshold.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_output_coordinator_class (Mock): Mocked OutputCoordinator class.
            mock_coordinator_class (Mock): Mocked OCRCoordinator class.
            mock_imread (Mock): Mocked cv2.imread function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            mock_stockpile (MagicMock): Mock stockpile from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        image_path = tmp_path / "test_screenshot.png"
        image_path.touch()

        database_path = tmp_path / "test.h5"
        database_path.touch()

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=0.92,
            early_exit=0.95,
            faction=None,
            language=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            output_destination=None,
            output_file=None,
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
        mock_output_coordinator_class.return_value = mock_handler

        await main()

        # Verify coordinator was created
        mock_coordinator_class.assert_called()

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

        database_path = tmp_path / "test.h5"
        database_path.touch()

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=None,
            early_exit=0.95,
            faction=None,
            language=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            output_destination=None,
            output_file=None,
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
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OutputCoordinator")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.setup_logging")
    async def test_main_with_quiet_mode(
        self,
        mock_setup_logging: Mock,
        mock_output_coordinator_class: Mock,
        mock_coordinator_class: Mock,
        mock_imread: Mock,
        mock_args: Mock,
        mock_stockpile: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with quiet mode enabled.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_output_coordinator_class (Mock): Mocked OutputCoordinator class.
            mock_coordinator_class (Mock): Mocked OCRCoordinator class.
            mock_imread (Mock): Mocked cv2.imread function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            mock_stockpile (MagicMock): Mock stockpile from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        image_path = tmp_path / "test_screenshot.png"
        image_path.touch()

        database_path = tmp_path / "test.h5"
        database_path.touch()

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=None,
            early_exit=0.95,
            faction=None,
            language=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=True,  # Quiet mode
            output_format=None,
            output_destination=None,
            output_file=None,
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
        mock_output_coordinator_class.return_value = mock_handler

        await main()

        # Verify setup_logging was called
        mock_setup_logging.assert_called_once()

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
        database_path = tmp_path / "test.h5"
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
            language=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            output_destination=None,
            output_file=None,
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

        database_path = tmp_path / "test.h5"
        database_path.touch()

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=None,
            early_exit=0.95,
            faction=None,
            language=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            output_destination=None,
            output_file=None,
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

        database_path = tmp_path / "test.h5"
        database_path.touch()

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=None,
            early_exit=0.95,
            faction=None,
            language=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            output_destination=None,
            output_file=None,
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

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.cv2.imread")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OCRCoordinator")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OutputCoordinator")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.setup_logging")
    async def test_main_with_language_filter(
        self,
        mock_setup_logging: Mock,
        mock_output_coordinator_class: Mock,
        mock_coordinator_class: Mock,
        mock_imread: Mock,
        mock_args: Mock,
        mock_stockpile: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with language filter.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_output_coordinator_class (Mock): Mocked OutputCoordinator class.
            mock_coordinator_class (Mock): Mocked OCRCoordinator class.
            mock_imread (Mock): Mocked cv2.imread function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            mock_stockpile (MagicMock): Mock stockpile from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        image_path = tmp_path / "test_screenshot.png"
        image_path.touch()

        database_path = tmp_path / "test.h5"
        database_path.touch()

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=None,
            early_exit=0.95,
            faction=None,
            language="fr",  # French language
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            output_destination=None,
            output_file=None,
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
        mock_output_coordinator_class.return_value = mock_handler

        await main()

        # Verify analyze_stockpile was called with French language parameter
        mock_coordinator.analyze_stockpile.assert_called_once()
        call_kwargs = mock_coordinator.analyze_stockpile.call_args[1]
        from foxhole_stockpiles.enums.supported_language import SupportedLanguage

        assert call_kwargs.get("languages") is not None
        assert call_kwargs.get("languages") == [SupportedLanguage.FRENCH]

    async def test_main_with_invalid_language(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test main function with invalid language code.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
            capsys (pytest.CaptureFixture[str]): Pytest fixture to capture output.
        """
        image_path = tmp_path / "test_screenshot.png"
        image_path.touch()

        database_path = tmp_path / "test.h5"
        database_path.touch()

        # Test with invalid language argument - argparse will handle the validation
        sys.argv = [
            "test",
            "--image",
            str(image_path),
            "--database",
            str(database_path),
            "--language",
            "invalid_lang",  # Invalid language
        ]

        # Should exit with code 2 for argparse validation error
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "invalid choice" in captured.err.lower()

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.get_app_settings")
    async def test_main_missing_database_path(
        self,
        mock_get_settings: Mock,
        mock_args: Mock,
        tmp_path: Path,
    ) -> None:
        """Test main function when database path is not provided.

        Args:
            mock_get_settings (Mock): Mocked get_app_settings function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        image_path = tmp_path / "test_screenshot.png"
        image_path.touch()

        # Mock settings with no database path
        mock_settings = MagicMock()
        mock_settings.scanner.database_path = None
        mock_get_settings.return_value = mock_settings

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=None,  # No database provided
            confidence=None,
            early_exit=0.95,
            faction=None,
            language=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            output_destination=None,
            output_file=None,
            config=None,
            token=None,
        )

        # Should exit with code 2 for argparse error
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 2

    @patch("argparse.ArgumentParser.parse_args")
    async def test_main_database_file_not_exists(
        self,
        mock_args: Mock,
        tmp_path: Path,
    ) -> None:
        """Test main function when database file does not exist.

        Args:
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        image_path = tmp_path / "test_screenshot.png"
        image_path.touch()

        database_path = tmp_path / "nonexistent.h5"  # Doesn't exist

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=None,
            early_exit=0.95,
            faction=None,
            language=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            output_destination=None,
            output_file=None,
            config=None,
            token=None,
        )

        # Should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1

    @patch("argparse.ArgumentParser.parse_args")
    async def test_main_database_path_is_directory(
        self,
        mock_args: Mock,
        tmp_path: Path,
    ) -> None:
        """Test main function when database path is a directory instead of a file.

        Args:
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        image_path = tmp_path / "test_screenshot.png"
        image_path.touch()

        database_path = tmp_path / "database_dir"
        database_path.mkdir()  # Create directory instead of file

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=None,
            early_exit=0.95,
            faction=None,
            language=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            output_destination=None,
            output_file=None,
            config=None,
            token=None,
        )

        # Should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.cv2.imread")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OCRCoordinator")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OutputCoordinator")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.setup_logging")
    async def test_main_with_token_argument(
        self,
        mock_setup_logging: Mock,
        mock_output_coordinator_class: Mock,
        mock_coordinator_class: Mock,
        mock_imread: Mock,
        mock_args: Mock,
        mock_stockpile: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with token argument for webhook output.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_output_coordinator_class (Mock): Mocked OutputCoordinator class.
            mock_coordinator_class (Mock): Mocked OCRCoordinator class.
            mock_imread (Mock): Mocked cv2.imread function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            mock_stockpile (MagicMock): Mock stockpile from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        image_path = tmp_path / "test_screenshot.png"
        image_path.touch()

        database_path = tmp_path / "test.h5"
        database_path.touch()

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=None,
            early_exit=0.95,
            faction=None,
            language=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            output_destination=None,
            output_file=None,
            config=None,
            token="test_webhook_token_123",  # Token provided
        )

        # Mock OCR coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.analyze_stockpile = AsyncMock(return_value=mock_stockpile)
        mock_coordinator_class.return_value = mock_coordinator

        # Mock output handler
        mock_handler = MagicMock()
        mock_handler.handle_output = AsyncMock(return_value=None)
        mock_output_coordinator_class.return_value = mock_handler

        await main()

        # Verify handle_output was called with token
        mock_handler.handle_output.assert_called_once()
        call_kwargs = mock_handler.handle_output.call_args[1]
        assert "token" in call_kwargs
        assert call_kwargs["token"] == "test_webhook_token_123"

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.cv2.imread")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OCRCoordinator")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OutputCoordinator")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.setup_logging")
    async def test_main_with_output_file_argument(
        self,
        mock_setup_logging: Mock,
        mock_output_coordinator_class: Mock,
        mock_coordinator_class: Mock,
        mock_imread: Mock,
        mock_args: Mock,
        mock_stockpile: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with output file argument.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_output_coordinator_class (Mock): Mocked OutputCoordinator class.
            mock_coordinator_class (Mock): Mocked OCRCoordinator class.
            mock_imread (Mock): Mocked cv2.imread function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            mock_stockpile (MagicMock): Mock stockpile from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        image_path = tmp_path / "test_screenshot.png"
        image_path.touch()

        database_path = tmp_path / "test.h5"
        database_path.touch()

        output_file = tmp_path / "output.json"

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=None,
            early_exit=0.95,
            faction=None,
            language=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            output_destination=None,
            output_file=output_file,  # Output file provided
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
        mock_output_coordinator_class.return_value = mock_handler

        await main()

        # Verify OutputCoordinator was created with file handler containing the output path
        mock_output_coordinator_class.assert_called_once()
        call_kwargs = mock_output_coordinator_class.call_args[1]
        output_settings = call_kwargs["output_settings"]
        assert len(output_settings.handlers) == 1
        assert output_settings.handlers[0].handler.path == str(output_file)


def test_main_module_importable() -> None:
    """Test that __main__ module can be imported without errors."""
    import foxhole_stockpiles.commands.stockpile_scanner.__main__  # noqa: F401


class TestMainModuleEntryPoint:
    """Test suite for __main__ module entry point."""

    def test_main_module_execution(self) -> None:
        """Test that the module can be executed as __main__."""
        from unittest.mock import AsyncMock, MagicMock

        mock_main = AsyncMock(return_value="stockpile_result")
        mock_print = MagicMock()
        mock_exit = MagicMock()
        mock_asyncio = MagicMock()
        mock_asyncio.run.return_value = "stockpile_result"

        # Simulate running as __main__
        exec(
            """
if __name__ == '__main__':
    stockpile = asyncio.run(main())
    print(stockpile)
    sys.exit(0)
""",
            {
                "__name__": "__main__",
                "asyncio": mock_asyncio,
                "main": mock_main,
                "print": mock_print,
                "sys": MagicMock(exit=mock_exit),
            },
        )
        mock_asyncio.run.assert_called_once()
        mock_print.assert_called_once_with("stockpile_result")
        mock_exit.assert_called_once_with(0)


class TestOutputDestinationHandling:
    """Test cases for different output destination configurations."""

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
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OutputCoordinator")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.setup_logging")
    async def test_main_with_console_destination(
        self,
        mock_setup_logging: Mock,
        mock_output_coordinator_class: Mock,
        mock_coordinator_class: Mock,
        mock_imread: Mock,
        mock_args: Mock,
        tmp_path: Path,
        mock_stockpile: Any,
    ) -> None:
        """Test main function with console output destination.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_output_coordinator_class (Mock): Mocked OutputCoordinator class.
            mock_coordinator_class (Mock): Mocked OCRCoordinator class.
            mock_imread (Mock): Mocked cv2.imread function.
            mock_args (Mock): Mocked argument parser.
            tmp_path (Path): Temporary directory path from pytest fixture.
            mock_stockpile (Any): Mock stockpile fixture.
        """
        image_path = tmp_path / "test.png"
        image_path.touch()
        database_path = tmp_path / "test.db"
        database_path.touch()

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=None,
            early_exit=0.95,
            faction=None,
            language=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            output_destination="console",
            output_file=None,
            config=None,
            token=None,
        )

        mock_imread.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

        mock_coordinator = MagicMock()
        mock_coordinator.analyze_stockpile = AsyncMock(return_value=mock_stockpile)
        mock_coordinator_class.return_value = mock_coordinator

        mock_handler = MagicMock()
        mock_handler.handle_output = AsyncMock(return_value=None)
        mock_output_coordinator_class.return_value = mock_handler

        await main()

        # Verify output coordinator was created with console handler
        mock_output_coordinator_class.assert_called_once()
        call_kwargs = mock_output_coordinator_class.call_args
        # The output settings should have a handler configured
        assert call_kwargs is not None

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.cv2.imread")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OCRCoordinator")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.OutputCoordinator")
    @patch("foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner.setup_logging")
    async def test_main_with_file_destination_and_output_destination_arg(
        self,
        mock_setup_logging: Mock,
        mock_output_coordinator_class: Mock,
        mock_coordinator_class: Mock,
        mock_imread: Mock,
        mock_args: Mock,
        tmp_path: Path,
        mock_stockpile: Any,
    ) -> None:
        """Test main function with explicit file output destination.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_output_coordinator_class (Mock): Mocked OutputCoordinator class.
            mock_coordinator_class (Mock): Mocked OCRCoordinator class.
            mock_imread (Mock): Mocked cv2.imread function.
            mock_args (Mock): Mocked argument parser.
            tmp_path (Path): Temporary directory path from pytest fixture.
            mock_stockpile (Any): Mock stockpile fixture.
        """
        image_path = tmp_path / "test.png"
        image_path.touch()
        database_path = tmp_path / "test.db"
        database_path.touch()
        output_file = tmp_path / "output.json"

        mock_args.return_value = argparse.Namespace(
            image=str(image_path),
            database=database_path,
            confidence=None,
            early_exit=0.95,
            faction=None,
            language=None,
            debug_image=False,
            log_file=None,
            verbose=False,
            quiet=False,
            output_format=None,
            output_destination="file",
            output_file=str(output_file),
            config=None,
            token=None,
        )

        mock_imread.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

        mock_coordinator = MagicMock()
        mock_coordinator.analyze_stockpile = AsyncMock(return_value=mock_stockpile)
        mock_coordinator_class.return_value = mock_coordinator

        mock_handler = MagicMock()
        mock_handler.handle_output = AsyncMock(return_value=None)
        mock_output_coordinator_class.return_value = mock_handler

        await main()

        # Verify output coordinator was created
        mock_output_coordinator_class.assert_called_once()
