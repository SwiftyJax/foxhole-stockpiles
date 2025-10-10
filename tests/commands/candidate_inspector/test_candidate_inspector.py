"""Tests for commands.candidate_inspector.candidate_inspector module.

This module contains comprehensive tests for the candidate inspector command,
including template manager interaction, icon matching, and filter application.
"""

import argparse
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from foxhole_stockpiles.commands.candidate_inspector.candidate_inspector import main
from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution


class TestCandidateInspectorMain:
    """Test suite for the candidate inspector main function.

    This class contains tests for the main entry point of the candidate
    inspector command, including argument parsing, filtering, and icon matching.
    """

    @pytest.fixture
    def mock_template_manager(self) -> MagicMock:
        """Create a mock template manager for testing.

        Returns:
            MagicMock: Configured mock TemplateManager instance.
        """
        manager = MagicMock()

        # Mock database with templates
        mock_db = MagicMock()
        mock_db.templates = []
        for i in range(10):
            template = MagicMock()
            template.code = f"TestItem{i}"
            template.faction = ItemFaction.NEUTRAL
            template.category = ItemCategory.Item
            template.crated = False
            template.mod = "vanilla"
            template.resolution = SupportedResolution.R_1080
            mock_db.templates.append(template)

        async def mock_load_database(resolution: SupportedResolution) -> MagicMock:
            return mock_db

        manager.load_database = mock_load_database

        async def mock_set_active_resolution(resolution: int) -> None:
            pass

        manager.set_active_resolution = mock_set_active_resolution

        # Mock match_icon to return candidates
        mock_match_result = MagicMock()
        mock_match_result.candidates = [0, 1, 2]
        mock_match_result.icon = None
        mock_match_result.confidence = 0.0
        manager.match_icon.return_value = mock_match_result

        return manager

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    async def test_main_with_basic_filters(
        self,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        mock_template_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with basic filter arguments.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_manager_class (Mock): Mocked TemplateManager class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            mock_template_manager (MagicMock): Mock template manager from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        mock_args.return_value = argparse.Namespace(
            database=db_path,
            code=None,
            faction=None,
            category=None,
            crated=None,
            mod=None,
            exclude_code=None,
            resolution="1080",
            icon=None,
            confidence=0.85,
            log_file=None,
            verbose=False,
            print=False,
            quiet=False,
        )

        mock_manager_class.return_value = mock_template_manager

        result = await main()

        # Verify template manager was created
        mock_manager_class.assert_called_once_with(database_path=db_path)

        # Verify match_icon was called with correct parameters
        assert mock_template_manager.match_icon.called

        # Result should be None since no icon was matched
        assert result is None

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.cv2.imread")
    async def test_main_with_icon_matching(
        self,
        mock_imread: Mock,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        mock_template_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with icon matching.

        Args:
            mock_imread (Mock): Mocked cv2.imread function.
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_manager_class (Mock): Mocked TemplateManager class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            mock_template_manager (MagicMock): Mock template manager from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        icon_path = tmp_path / "icon.png"
        icon_path.touch()

        # Mock image loading
        mock_image = np.zeros((64, 64, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        # Configure match result with an icon match
        mock_icon = MagicMock()
        mock_icon.code = "TestRifle"
        mock_icon.crated = False
        mock_icon.faction = ItemFaction.NEUTRAL
        mock_icon.category = ItemCategory.Item
        mock_icon.mod = "vanilla"
        mock_icon.resolution = SupportedResolution.R_1080
        mock_icon.model_dump.return_value = {
            "code": "TestRifle",
            "crated": False,
            "faction": "neutral",
            "category": "weapon",
            "mod": "vanilla",
            "resolution": "1080",
        }

        mock_match_result = MagicMock()
        mock_match_result.candidates = [0, 1, 2]
        mock_match_result.icon = mock_icon
        mock_match_result.confidence = 0.92
        mock_template_manager.match_icon.return_value = mock_match_result

        mock_args.return_value = argparse.Namespace(
            database=db_path,
            code=None,
            faction=None,
            category=None,
            crated=None,
            mod=None,
            exclude_code=None,
            resolution="1080",
            icon=icon_path,
            confidence=0.85,
            log_file=None,
            verbose=False,
            print=False,
            quiet=False,
        )

        mock_manager_class.return_value = mock_template_manager

        result = await main()

        # Verify icon was loaded
        mock_imread.assert_called_once()

        # Verify match_icon was called with the image
        assert mock_template_manager.match_icon.called
        call_args = mock_template_manager.match_icon.call_args
        assert call_args[1]["icon_image"] is not None

        # Result should contain match data
        assert result is not None
        assert result["code"] == "TestRifle"
        assert result["confidence"] == 0.92

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    async def test_main_with_faction_filter(
        self,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        mock_template_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with faction filter.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_manager_class (Mock): Mocked TemplateManager class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            mock_template_manager (MagicMock): Mock template manager from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        mock_args.return_value = argparse.Namespace(
            database=db_path,
            code=None,
            faction="c",
            category=None,
            crated=None,
            mod=None,
            exclude_code=None,
            resolution="1080",
            icon=None,
            confidence=0.85,
            log_file=None,
            verbose=False,
            print=True,
            quiet=False,
        )

        mock_manager_class.return_value = mock_template_manager

        await main()

        # Verify match_icon was called with faction filter
        mock_template_manager.match_icon.assert_called()
        call_args = mock_template_manager.match_icon.call_args
        assert call_args[1]["faction"] == ItemFaction.COLONIALS

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    async def test_main_database_not_found(
        self,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        tmp_path: Path,
    ) -> None:
        """Test main function when database file is not found.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_manager_class (Mock): Mocked TemplateManager class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "nonexistent.pkl"

        mock_args.return_value = argparse.Namespace(
            database=db_path,
            code=None,
            faction=None,
            category=None,
            crated=None,
            mod=None,
            exclude_code=None,
            resolution="1080",
            icon=None,
            confidence=0.85,
            log_file=None,
            verbose=False,
            print=False,
            quiet=False,
        )

        # Mock template manager to raise FileNotFoundError
        manager = MagicMock()

        async def mock_load_database(resolution: SupportedResolution) -> None:
            raise FileNotFoundError("Database file not found")

        manager.load_database = mock_load_database
        mock_manager_class.return_value = manager

        # Should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    async def test_main_with_invalid_confidence(
        self,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        tmp_path: Path,
    ) -> None:
        """Test main function with invalid confidence value.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_manager_class (Mock): Mocked TemplateManager class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        mock_args.return_value = argparse.Namespace(
            database=db_path,
            code=None,
            faction=None,
            category=None,
            crated=None,
            mod=None,
            exclude_code=None,
            resolution="1080",
            icon=None,
            confidence=1.5,  # Invalid: > 1
            log_file=None,
            verbose=False,
            print=False,
            quiet=False,
        )

        mock_manager_class.return_value = MagicMock()

        # Should exit with code 2 for argparse validation error
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 2

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    async def test_main_with_invalid_resolution(
        self,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        tmp_path: Path,
    ) -> None:
        """Test main function with invalid resolution value.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_manager_class (Mock): Mocked TemplateManager class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        mock_args.return_value = argparse.Namespace(
            database=db_path,
            code=None,
            faction=None,
            category=None,
            crated=None,
            mod=None,
            exclude_code=None,
            resolution="999",  # Invalid resolution
            icon=None,
            confidence=0.85,
            log_file=None,
            verbose=False,
            print=False,
            quiet=False,
        )

        mock_manager_class.return_value = MagicMock()

        # Should exit with code 2 for argparse validation error
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 2

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    async def test_main_with_code_filter(
        self,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        mock_template_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with code filter.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_manager_class (Mock): Mocked TemplateManager class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            mock_template_manager (MagicMock): Mock template manager from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        mock_args.return_value = argparse.Namespace(
            database=db_path,
            code="TestRifle",  # Filter by code
            faction=None,
            category=None,
            crated=None,
            mod=None,
            exclude_code=None,
            resolution="1080",
            icon=None,
            confidence=0.85,
            log_file=None,
            verbose=False,
            print=False,
            quiet=False,
        )

        mock_manager_class.return_value = mock_template_manager

        await main()

        # Verify match_icon was called with code filter
        mock_template_manager.match_icon.assert_called()
        call_args = mock_template_manager.match_icon.call_args
        assert call_args[1]["code"] == "TestRifle"

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    async def test_main_with_category_filter(
        self,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        mock_template_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with category filter.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_manager_class (Mock): Mocked TemplateManager class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            mock_template_manager (MagicMock): Mock template manager from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        mock_args.return_value = argparse.Namespace(
            database=db_path,
            code=None,
            faction=None,
            category="item",  # Filter by category
            crated=None,
            mod=None,
            exclude_code=None,
            resolution="1080",
            icon=None,
            confidence=0.85,
            log_file=None,
            verbose=False,
            print=False,
            quiet=False,
        )

        mock_manager_class.return_value = mock_template_manager

        await main()

        # Verify match_icon was called with category filter
        mock_template_manager.match_icon.assert_called()
        call_args = mock_template_manager.match_icon.call_args
        assert call_args[1]["category"] == ItemCategory.Item

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    async def test_main_with_mod_filter(
        self,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        mock_template_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with mod filter.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_manager_class (Mock): Mocked TemplateManager class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            mock_template_manager (MagicMock): Mock template manager from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        mock_args.return_value = argparse.Namespace(
            database=db_path,
            code=None,
            faction=None,
            category=None,
            crated=None,
            mod="custom_mod",  # Filter by mod
            exclude_code=None,
            resolution="1080",
            icon=None,
            confidence=0.85,
            log_file=None,
            verbose=False,
            print=False,
            quiet=False,
        )

        mock_manager_class.return_value = mock_template_manager

        await main()

        # Verify match_icon was called with mod filter
        mock_template_manager.match_icon.assert_called()
        call_args = mock_template_manager.match_icon.call_args
        assert call_args[1]["mod"] == "custom_mod"

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    async def test_main_with_crated_filter(
        self,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        mock_template_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with crated filter.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_manager_class (Mock): Mocked TemplateManager class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            mock_template_manager (MagicMock): Mock template manager from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        mock_args.return_value = argparse.Namespace(
            database=db_path,
            code=None,
            faction=None,
            category=None,
            crated="true",  # Filter by crated (string, converted to bool)
            mod=None,
            exclude_code=None,
            resolution="1080",
            icon=None,
            confidence=0.85,
            log_file=None,
            verbose=False,
            print=False,
            quiet=False,
        )

        mock_manager_class.return_value = mock_template_manager

        await main()

        # Verify match_icon was called with crated filter
        mock_template_manager.match_icon.assert_called()
        call_args = mock_template_manager.match_icon.call_args
        assert call_args[1]["crated"] is True

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.cv2.imread")
    async def test_main_with_missing_icon_file(
        self,
        mock_imread: Mock,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        tmp_path: Path,
    ) -> None:
        """Test main function when icon file is missing.

        Args:
            mock_imread (Mock): Mocked cv2.imread function.
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_manager_class (Mock): Mocked TemplateManager class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        icon_path = tmp_path / "missing.png"  # File doesn't exist

        mock_args.return_value = argparse.Namespace(
            database=db_path,
            code=None,
            faction=None,
            category=None,
            crated=None,
            mod=None,
            exclude_code=None,
            resolution="1080",
            icon=icon_path,
            confidence=0.85,
            log_file=None,
            verbose=False,
            print=False,
            quiet=False,
        )

        # imread returns None for missing files
        mock_imread.return_value = None

        # Mock template manager with async methods
        manager = MagicMock()

        async def mock_load_database(resolution: SupportedResolution) -> MagicMock:
            return MagicMock()

        async def mock_set_active_resolution(resolution: int) -> None:
            pass

        manager.load_database = mock_load_database
        manager.set_active_resolution = mock_set_active_resolution
        mock_manager_class.return_value = manager

        # Should exit with code 1 for missing icon
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1
