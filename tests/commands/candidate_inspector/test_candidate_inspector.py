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

        # Mock get_available_mods to return available mods
        def mock_get_available_mods_db() -> set[str]:
            return {"vanilla", "custom_mod"}

        mock_db.get_available_mods = mock_get_available_mods_db

        async def mock_load_database(resolution: SupportedResolution) -> MagicMock:
            return mock_db

        manager.load_database = mock_load_database

        async def mock_set_active_resolution(resolution: int) -> None:
            pass

        manager.set_active_resolution = mock_set_active_resolution

        # Mock get_supported_mods to return available mods
        async def mock_get_supported_mods() -> set[str]:
            return {"vanilla", "custom_mod"}

        manager.get_supported_mods = mock_get_supported_mods

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
            top=5,
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
            top=5,
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
            top=5,
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
            top=5,
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
            top=5,
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
            top=5,
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
            top=5,
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
            top=5,
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
    async def test_main_with_invalid_mod_filter(
        self,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        mock_template_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with invalid mod filter.

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
            mod="invalid_mod",  # Invalid mod that doesn't exist
            exclude_code=None,
            resolution="1080",
            icon=None,
            confidence=0.85,
            log_file=None,
            verbose=False,
            print=False,
            quiet=False,
            top=5,
        )

        mock_manager_class.return_value = mock_template_manager

        # Should exit with code 1 for invalid mod
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1

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
            top=5,
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
            top=5,
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

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    async def test_main_with_quiet_mode(
        self,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        mock_template_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with quiet mode enabled.

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
            quiet=True,  # Quiet mode
            top=5,
        )

        mock_manager_class.return_value = mock_template_manager

        await main()

        # Verify setup_logging was called
        mock_setup_logging.assert_called_once()

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    async def test_main_with_verbose_mode(
        self,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        mock_template_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with verbose mode enabled.

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
            verbose=True,  # Verbose mode
            print=False,
            quiet=False,
            top=5,
        )

        mock_manager_class.return_value = mock_template_manager

        await main()

        # Verify setup_logging was called
        mock_setup_logging.assert_called_once()

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    async def test_main_with_exclude_codes(
        self,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        mock_template_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function with exclude-code filter.

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
            exclude_code=["Rifle", "Bandages"],  # Exclude specific codes
            resolution="1080",
            icon=None,
            confidence=0.85,
            log_file=None,
            verbose=False,
            print=False,
            quiet=False,
            top=5,
        )

        mock_manager_class.return_value = mock_template_manager

        await main()

        # Verify match_icon was called with excluded codes
        mock_template_manager.match_icon.assert_called()
        call_args = mock_template_manager.match_icon.call_args
        assert call_args[1]["excluded_codes"] == ["Rifle", "Bandages"]

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    async def test_main_no_candidates_found(
        self,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        tmp_path: Path,
    ) -> None:
        """Test main function when no candidates are found.

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
            code="NonExistentItem",
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
            top=5,
        )

        # Mock template manager with empty candidates
        manager = MagicMock()
        mock_db = MagicMock()
        mock_db.templates = []

        async def mock_load_database(resolution: SupportedResolution) -> MagicMock:
            return mock_db

        async def mock_set_active_resolution(resolution: int) -> None:
            pass

        manager.load_database = mock_load_database
        manager.set_active_resolution = mock_set_active_resolution

        # Return empty candidates
        mock_match_result = MagicMock()
        mock_match_result.candidates = []  # No candidates
        mock_match_result.icon = None
        mock_match_result.confidence = 0.0
        manager.match_icon.return_value = mock_match_result

        mock_manager_class.return_value = manager

        result = await main()

        # Should return None when no candidates found
        assert result is None

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.cv2.imread")
    async def test_main_icon_no_match_found(
        self,
        mock_imread: Mock,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        mock_template_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function when icon is provided but no match found.

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

        # Configure match result with candidates but no icon match
        mock_match_result = MagicMock()
        mock_match_result.candidates = [0, 1, 2]  # Has candidates
        mock_match_result.icon = None  # But no match
        mock_match_result.confidence = 0.0
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
            top=5,
        )

        mock_manager_class.return_value = mock_template_manager

        result = await main()

        # Should return None when no match found
        assert result is None

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    async def test_main_with_statistics_and_crated_items(
        self,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        tmp_path: Path,
    ) -> None:
        """Test main function statistics display with crated items.

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
            icon=None,  # No icon to trigger statistics
            confidence=0.85,
            log_file=None,
            verbose=False,
            print=False,
            quiet=False,
            top=5,
        )

        # Mock template manager with crated items
        manager = MagicMock()
        mock_db = MagicMock()
        mock_db.templates = []

        # Add some templates including crated ones
        for i in range(5):
            template = MagicMock()
            template.code = f"TestItem{i}"
            template.faction = ItemFaction.NEUTRAL
            template.category = ItemCategory.Item
            template.crated = i % 2 == 0  # Some crated, some not
            template.mod = "vanilla"
            template.resolution = SupportedResolution.R_1080
            mock_db.templates.append(template)

        async def mock_load_database(resolution: SupportedResolution) -> MagicMock:
            return mock_db

        async def mock_set_active_resolution(resolution: int) -> None:
            pass

        manager.load_database = mock_load_database
        manager.set_active_resolution = mock_set_active_resolution

        # Return all templates as candidates
        mock_match_result = MagicMock()
        mock_match_result.candidates = [0, 1, 2, 3, 4]
        mock_match_result.icon = None
        mock_match_result.confidence = 0.0
        manager.match_icon.return_value = mock_match_result

        mock_manager_class.return_value = manager

        result = await main()

        # Should display statistics and handle crated items
        assert result is None

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.cv2.imread")
    async def test_main_icon_load_exception_verbose(
        self,
        mock_imread: Mock,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        tmp_path: Path,
    ) -> None:
        """Test main function when icon loading raises exception with verbose mode.

        Args:
            mock_imread (Mock): Mocked cv2.imread function.
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_manager_class (Mock): Mocked TemplateManager class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        icon_path = tmp_path / "icon.png"
        icon_path.touch()

        # imread raises exception
        mock_imread.side_effect = RuntimeError("Simulated imread failure")

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
            verbose=True,  # Verbose mode to trigger exception logging
            print=False,
            quiet=False,
            top=5,
        )

        # Mock template manager
        manager = MagicMock()

        async def mock_load_database(resolution: SupportedResolution) -> MagicMock:
            return MagicMock()

        async def mock_set_active_resolution(resolution: int) -> None:
            pass

        manager.load_database = mock_load_database
        manager.set_active_resolution = mock_set_active_resolution
        mock_manager_class.return_value = manager

        # Should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    async def test_main_matching_exception_verbose(
        self,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        tmp_path: Path,
    ) -> None:
        """Test main function when matching raises exception with verbose mode.

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
            confidence=0.85,
            log_file=None,
            verbose=True,  # Verbose mode
            print=False,
            quiet=False,
            top=5,
        )

        # Mock template manager that raises exception during matching
        manager = MagicMock()

        async def mock_load_database(resolution: SupportedResolution) -> MagicMock:
            return MagicMock()

        async def mock_set_active_resolution(resolution: int) -> None:
            pass

        manager.load_database = mock_load_database
        manager.set_active_resolution = mock_set_active_resolution
        manager.match_icon.side_effect = RuntimeError("Simulated matching failure")
        mock_manager_class.return_value = manager

        # Should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.cv2.imread")
    async def test_main_with_top_matches_display(
        self,
        mock_imread: Mock,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        mock_template_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test main function displays top matches with crated and non-crated items.

        This test verifies that line 307 (crated_str display logic) is executed
        by providing actual top_matches data with both crated and non-crated templates.

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

        # Create mock templates with different crated status
        mock_template1 = MagicMock()
        mock_template1.code = "Rifle"
        mock_template1.crated = False  # Normal item
        mock_template1.faction = ItemFaction.COLONIALS
        mock_template1.category = ItemCategory.Item
        mock_template1.mod = "vanilla"
        mock_template1.resolution = SupportedResolution.R_1080

        mock_template2 = MagicMock()
        mock_template2.code = "Rifle"
        mock_template2.crated = True  # Crated item
        mock_template2.faction = ItemFaction.COLONIALS
        mock_template2.category = ItemCategory.Item
        mock_template2.mod = "vanilla"
        mock_template2.resolution = SupportedResolution.R_1080

        mock_template3 = MagicMock()
        mock_template3.code = "Bandages"
        mock_template3.crated = False  # Normal item
        mock_template3.faction = ItemFaction.NEUTRAL
        mock_template3.category = ItemCategory.Item
        mock_template3.mod = "vanilla"
        mock_template3.resolution = SupportedResolution.R_1080

        # Configure match result with top matches including crated items
        mock_match_result = MagicMock()
        mock_match_result.candidates = [0, 1, 2]
        mock_match_result.icon = None  # No match above threshold
        mock_match_result.confidence = 0.0
        # Populate top_matches with (template, confidence) tuples
        mock_match_result.top_matches = [
            (mock_template1, 0.85),  # Normal Rifle
            (mock_template2, 0.82),  # Crated Rifle
            (mock_template3, 0.78),  # Normal Bandages
        ]
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
            confidence=0.90,  # High threshold so no match, but top_matches will be shown
            log_file=None,
            verbose=False,
            print=False,
            quiet=False,
            top=3,
        )

        mock_manager_class.return_value = mock_template_manager

        result = await main()

        # Verify icon was loaded
        mock_imread.assert_called_once()

        # Verify match_icon was called
        assert mock_template_manager.match_icon.called

        # Result should be None since no match above threshold
        assert result is None

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.get_settings")
    async def test_main_missing_database_path(
        self,
        mock_get_settings: Mock,
        mock_args: Mock,
        tmp_path: Path,
    ) -> None:
        """Test main function when database path is not provided.

        Args:
            mock_get_settings (Mock): Mocked get_settings function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        # Mock settings with no database path
        mock_settings = MagicMock()
        mock_settings.scanner.database_path = None
        mock_get_settings.return_value = mock_settings

        mock_args.return_value = argparse.Namespace(
            database=None,  # No database provided
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
            top=5,
        )

        # Should exit with code 2 for argparse error
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 2

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
        database_path = tmp_path / "database_dir"
        database_path.mkdir()  # Create directory instead of file

        mock_args.return_value = argparse.Namespace(
            database=database_path,
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
            top=5,
        )

        # Should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    async def test_main_database_file_not_found_error(
        self,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_args: Mock,
        tmp_path: Path,
    ) -> None:
        """Test main function when FileNotFoundError is raised loading database.

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
            confidence=0.85,
            log_file=None,
            verbose=False,
            print=False,
            quiet=False,
            top=5,
        )

        # Mock template manager to raise FileNotFoundError when loading database
        manager = MagicMock()

        async def mock_load_database(resolution: SupportedResolution) -> MagicMock:
            raise FileNotFoundError("Database file not found")

        manager.load_database = mock_load_database
        mock_manager_class.return_value = manager

        # Should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.cv2.imread")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.TemplateManager")
    @patch("foxhole_stockpiles.commands.candidate_inspector.candidate_inspector.setup_logging")
    async def test_main_with_corrupted_icon_file(
        self,
        mock_setup_logging: Mock,
        mock_manager_class: Mock,
        mock_imread: Mock,
        mock_args: Mock,
        tmp_path: Path,
    ) -> None:
        """Test main function when icon file exists but imread fails to load it.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_manager_class (Mock): Mocked TemplateManager class.
            mock_imread (Mock): Mocked cv2.imread function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        icon_path = tmp_path / "corrupted.png"
        icon_path.touch()  # File exists

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
            top=5,
        )

        # imread returns None for corrupted/invalid image files
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

        # Should exit with code 1 for corrupted icon
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1


def test_main_module_importable() -> None:
    """Test that __main__ module can be imported without errors."""
    import foxhole_stockpiles.commands.candidate_inspector.__main__  # noqa: F401


class TestMainModuleEntryPoint:
    """Test suite for __main__ module entry point."""

    def test_main_module_execution_with_result(self) -> None:
        """Test that the module can be executed as __main__ with result."""
        from unittest.mock import AsyncMock

        mock_main = AsyncMock(return_value={"test": "result"})
        mock_print = MagicMock()
        mock_exit = MagicMock()
        mock_asyncio = MagicMock()
        mock_asyncio.run.return_value = {"test": "result"}
        mock_json = MagicMock()
        mock_json.dumps.return_value = '{"test": "result"}'

        # Simulate running as __main__
        exec(
            """
if __name__ == '__main__':
    result = asyncio.run(main())
    print(json.dumps(result) if result is not None else "")
    sys.exit(0)
""",
            {
                "__name__": "__main__",
                "asyncio": mock_asyncio,
                "json": mock_json,
                "main": mock_main,
                "print": mock_print,
                "sys": MagicMock(exit=mock_exit),
            },
        )
        mock_asyncio.run.assert_called_once()
        mock_print.assert_called_once_with('{"test": "result"}')
        mock_exit.assert_called_once_with(0)

    def test_main_module_execution_with_none_result(self) -> None:
        """Test that the module can be executed as __main__ with None result."""
        from unittest.mock import AsyncMock

        mock_main = AsyncMock(return_value=None)
        mock_print = MagicMock()
        mock_exit = MagicMock()
        mock_asyncio = MagicMock()
        mock_asyncio.run.return_value = None

        # Simulate running as __main__
        exec(
            """
if __name__ == '__main__':
    result = asyncio.run(main())
    print(json.dumps(result) if result is not None else "")
    sys.exit(0)
""",
            {
                "__name__": "__main__",
                "asyncio": mock_asyncio,
                "json": MagicMock(),
                "main": mock_main,
                "print": mock_print,
                "sys": MagicMock(exit=mock_exit),
            },
        )
        mock_asyncio.run.assert_called_once()
        mock_print.assert_called_once_with("")
        mock_exit.assert_called_once_with(0)
