"""Tests for commands.add_icon.add_icon module.

This module contains comprehensive tests for the add icon command,
including IconAdder class functionality, icon addition, and database
update operations.
"""

import argparse
import pickle
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import cv2
import numpy as np
import pytest

from foxhole_stockpiles.commands.add_icon.add_icon import IconAdder, main
from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.models.icon_template import IconTemplate
from foxhole_stockpiles.services.template_database import TemplateDatabase


@pytest.fixture
def sample_database_file(tmp_path: Path) -> Path:
    """Create a sample database file for testing.

    Args:
        tmp_path (Path): Temporary directory path from pytest fixture.

    Returns:
        Path: Path to the created sample database file.
    """
    db_path = tmp_path / "test_database.pkl"

    # Create databases with actual templates
    databases: dict[SupportedResolution, TemplateDatabase] = {}

    for resolution in [SupportedResolution.R_1080, SupportedResolution.R_1440]:
        db = TemplateDatabase(resolution)

        # Add a sample template
        template = IconTemplate(
            code="TestItem",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            crated=False,
            mod="vanilla",
            resolution=resolution,
            image=np.zeros((32, 32, 3), dtype=np.uint8),
            phash=0,
        )
        db.add_template(template)
        databases[resolution] = db

    # Save to file
    with open(db_path, "wb") as f:
        pickle.dump(databases, f, protocol=pickle.HIGHEST_PROTOCOL)

    return db_path


@pytest.fixture
def sample_icon_file(tmp_path: Path) -> Path:
    """Create a sample icon file for testing.

    Args:
        tmp_path (Path): Temporary directory path from pytest fixture.

    Returns:
        Path: Path to the created sample icon file.
    """
    icon_path = tmp_path / "test_icon.png"

    # Create a 32x32 test image (correct size for 1080p)
    # Icon scaling: 64 / 2160 * 1080 = 32
    test_image = np.zeros((32, 32, 3), dtype=np.uint8)
    test_image[8:24, 8:24] = [255, 128, 0]  # Orange square

    cv2.imwrite(str(icon_path), test_image)

    return icon_path


class TestIconAdderInitialization:
    """Test suite for IconAdder initialization.

    This class contains tests for IconAdder instance creation
    with various parameter combinations and configurations.
    """

    async def test_initialization_with_valid_database(self, sample_database_file: Path) -> None:
        """Test IconAdder initialization with valid database.

        Args:
            sample_database_file (Path): Sample database file from fixture.
        """
        adder = IconAdder(database_path=sample_database_file)

        assert adder.database_path == sample_database_file
        assert len(adder.databases) == 2
        assert SupportedResolution.R_1080 in adder.databases
        assert SupportedResolution.R_1440 in adder.databases

    async def test_initialization_with_nonexistent_database(self, tmp_path: Path) -> None:
        """Test IconAdder initialization with nonexistent database.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "nonexistent.pkl"

        with pytest.raises(FileNotFoundError, match="Database file not found"):
            IconAdder(database_path=db_path)

    async def test_initialization_with_invalid_database(self, tmp_path: Path) -> None:
        """Test IconAdder initialization with invalid database file.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "invalid.pkl"
        db_path.write_text("invalid content")

        with pytest.raises(ValueError, match="Failed to load database"):
            IconAdder(database_path=db_path)

    async def test_initialization_with_empty_database(self, tmp_path: Path) -> None:
        """Test IconAdder initialization with empty database.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "empty.pkl"

        # Create empty database
        with open(db_path, "wb") as f:
            pickle.dump({}, f)

        with pytest.raises(ValueError, match="No databases found"):
            IconAdder(database_path=db_path)


class TestIconAdderMethods:
    """Test suite for IconAdder methods.

    This class contains tests for the core functionality of IconAdder
    including icon addition, database saving, and error handling.
    """

    @pytest.fixture
    def adder(self, sample_database_file: Path) -> IconAdder:
        """Create an IconAdder instance for testing.

        Args:
            sample_database_file (Path): Sample database file from fixture.

        Returns:
            IconAdder: Configured adder instance for testing.
        """
        return IconAdder(database_path=sample_database_file)

    async def test_add_icon_success(self, adder: IconAdder, sample_icon_file: Path) -> None:
        """Test adding icon successfully.

        Args:
            adder (IconAdder): IconAdder instance from fixture.
            sample_icon_file (Path): Sample icon file from fixture.
        """
        initial_count = len(adder.databases[SupportedResolution.R_1080].templates)

        await adder.add_icon(
            icon_path=sample_icon_file,
            item_code="NewItem",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            crated=False,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
        )

        # Verify template was added
        final_count = len(adder.databases[SupportedResolution.R_1080].templates)
        assert final_count == initial_count + 1

        # Verify template properties
        new_template = adder.databases[SupportedResolution.R_1080].templates[-1]
        assert new_template.code == "NewItem"
        assert new_template.faction == ItemFaction.NEUTRAL
        assert new_template.category == ItemCategory.Item
        assert new_template.crated is False
        assert new_template.mod == "vanilla"

    async def test_add_icon_crated_variant(self, adder: IconAdder, sample_icon_file: Path) -> None:
        """Test adding crated icon variant.

        Args:
            adder (IconAdder): IconAdder instance from fixture.
            sample_icon_file (Path): Sample icon file from fixture.
        """
        await adder.add_icon(
            icon_path=sample_icon_file,
            item_code="CratedItem",
            faction=ItemFaction.COLONIALS,
            category=ItemCategory.Vehicle,
            crated=True,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
        )

        # Verify crated template was added
        new_template = adder.databases[SupportedResolution.R_1080].templates[-1]
        assert new_template.code == "CratedItem"
        assert new_template.crated is True
        assert new_template.faction == ItemFaction.COLONIALS
        assert new_template.category == ItemCategory.Vehicle

    async def test_add_icon_with_nonexistent_file(self, adder: IconAdder) -> None:
        """Test adding icon with nonexistent file.

        Args:
            adder (IconAdder): IconAdder instance from fixture.
        """
        fake_path = Path("nonexistent_icon.png")

        with pytest.raises(FileNotFoundError, match="Icon file not found"):
            await adder.add_icon(
                icon_path=fake_path,
                item_code="Item",
                faction=ItemFaction.NEUTRAL,
                category=ItemCategory.Item,
                crated=False,
                mod="vanilla",
                resolution=SupportedResolution.R_1080,
            )

    async def test_add_icon_with_invalid_resolution(
        self, adder: IconAdder, sample_icon_file: Path
    ) -> None:
        """Test adding icon with resolution not in database.

        Args:
            adder (IconAdder): IconAdder instance from fixture.
            sample_icon_file (Path): Sample icon file from fixture.
        """
        with pytest.raises(ValueError, match="Resolution .* not found in database"):
            await adder.add_icon(
                icon_path=sample_icon_file,
                item_code="Item",
                faction=ItemFaction.NEUTRAL,
                category=ItemCategory.Item,
                crated=False,
                mod="vanilla",
                resolution=SupportedResolution.R_2160,  # Not in test database
            )

    @patch("cv2.imread")
    async def test_add_icon_with_failed_image_load(
        self, mock_imread: Mock, adder: IconAdder, sample_icon_file: Path
    ) -> None:
        """Test adding icon when image fails to load.

        Args:
            mock_imread (Mock): Mocked cv2.imread function.
            adder (IconAdder): IconAdder instance from fixture.
            sample_icon_file (Path): Sample icon file from fixture.
        """
        mock_imread.return_value = None

        with pytest.raises(ValueError, match="Failed to load icon image"):
            await adder.add_icon(
                icon_path=sample_icon_file,
                item_code="Item",
                faction=ItemFaction.NEUTRAL,
                category=ItemCategory.Item,
                crated=False,
                mod="vanilla",
                resolution=SupportedResolution.R_1080,
            )

    async def test_add_icon_multiple_factions(
        self, adder: IconAdder, sample_icon_file: Path
    ) -> None:
        """Test adding icons with different factions.

        Args:
            adder (IconAdder): IconAdder instance from fixture.
            sample_icon_file (Path): Sample icon file from fixture.
        """
        # Add Colonial icon
        await adder.add_icon(
            icon_path=sample_icon_file,
            item_code="ColonialItem",
            faction=ItemFaction.COLONIALS,
            category=ItemCategory.Item,
            crated=False,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
        )

        # Add Warden icon
        await adder.add_icon(
            icon_path=sample_icon_file,
            item_code="WardenItem",
            faction=ItemFaction.WARDENS,
            category=ItemCategory.Item,
            crated=False,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
        )

        # Verify both were added
        templates = adder.databases[SupportedResolution.R_1080].templates
        colonial_templates = [t for t in templates if t.faction == ItemFaction.COLONIALS]
        warden_templates = [t for t in templates if t.faction == ItemFaction.WARDENS]

        assert len(colonial_templates) >= 1
        assert len(warden_templates) >= 1

    async def test_add_icon_custom_mod(self, adder: IconAdder, sample_icon_file: Path) -> None:
        """Test adding icon with custom mod name.

        Args:
            adder (IconAdder): IconAdder instance from fixture.
            sample_icon_file (Path): Sample icon file from fixture.
        """
        await adder.add_icon(
            icon_path=sample_icon_file,
            item_code="ModItem",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            crated=False,
            mod="custom_mod",
            resolution=SupportedResolution.R_1080,
        )

        # Verify mod name
        new_template = adder.databases[SupportedResolution.R_1080].templates[-1]
        assert new_template.mod == "custom_mod"

    async def test_add_icon_with_wrong_dimensions(self, adder: IconAdder, tmp_path: Path) -> None:
        """Test adding icon with incorrect dimensions.

        Args:
            adder (IconAdder): IconAdder instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        # Create icon with wrong size (16x16 instead of 32x32 for 1080p)
        wrong_size_icon = tmp_path / "wrong_size.png"
        wrong_image = np.zeros((16, 16, 3), dtype=np.uint8)
        cv2.imwrite(str(wrong_size_icon), wrong_image)

        with pytest.raises(ValueError, match="Icon has incorrect dimensions"):
            await adder.add_icon(
                icon_path=wrong_size_icon,
                item_code="WrongSize",
                faction=ItemFaction.NEUTRAL,
                category=ItemCategory.Item,
                crated=False,
                mod="vanilla",
                resolution=SupportedResolution.R_1080,
            )

    async def test_add_duplicate_icon_without_replace(
        self, adder: IconAdder, sample_icon_file: Path
    ) -> None:
        """Test that adding duplicate icon without replace flag fails.

        Args:
            adder (IconAdder): IconAdder instance from fixture.
            sample_icon_file (Path): Sample icon file from fixture.
        """
        # Add icon first time
        await adder.add_icon(
            icon_path=sample_icon_file,
            item_code="DuplicateTest",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            crated=False,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
        )

        # Try to add same icon again without replace flag
        with pytest.raises(ValueError, match="Icon already exists"):
            await adder.add_icon(
                icon_path=sample_icon_file,
                item_code="DuplicateTest",
                faction=ItemFaction.NEUTRAL,
                category=ItemCategory.Item,
                crated=False,
                mod="vanilla",
                resolution=SupportedResolution.R_1080,
                replace=False,
            )

    async def test_replace_existing_icon(
        self, adder: IconAdder, sample_icon_file: Path, tmp_path: Path
    ) -> None:
        """Test replacing existing icon with replace flag.

        Args:
            adder (IconAdder): IconAdder instance from fixture.
            sample_icon_file (Path): Sample icon file from fixture.
            tmp_path (Path): Temporary directory path from fixture.
        """
        # Add icon first time
        await adder.add_icon(
            icon_path=sample_icon_file,
            item_code="ReplaceTest",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            crated=False,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
        )

        initial_count = len(adder.databases[SupportedResolution.R_1080].templates)

        # Create a different icon with same size
        new_icon_file = tmp_path / "new_icon.png"
        new_image = np.zeros((32, 32, 3), dtype=np.uint8)
        new_image[8:24, 8:24] = [0, 255, 0]  # Green square
        cv2.imwrite(str(new_icon_file), new_image)

        # Replace with new icon
        await adder.add_icon(
            icon_path=new_icon_file,
            item_code="ReplaceTest",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            crated=False,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
            replace=True,
        )

        # Verify count didn't increase (replaced, not added)
        final_count = len(adder.databases[SupportedResolution.R_1080].templates)
        assert final_count == initial_count

        # Verify the icon was actually replaced (check it's the new image)
        template = None
        for t in adder.databases[SupportedResolution.R_1080].templates:
            if t.code == "ReplaceTest":
                template = t
                break

        assert template is not None
        # Check that the new image has green pixels (from new icon)
        assert np.any(template.image[:, :, 1] > 200)  # Green channel

    async def test_save_databases(self, adder: IconAdder, sample_icon_file: Path) -> None:
        """Test saving databases to file.

        Args:
            adder (IconAdder): IconAdder instance from fixture.
            sample_icon_file (Path): Sample icon file from fixture.
        """
        # Add an icon
        await adder.add_icon(
            icon_path=sample_icon_file,
            item_code="SaveTest",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            crated=False,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
        )

        # Save databases
        await adder.save_databases()

        # Verify file exists
        assert adder.database_path.exists()

        # Verify backup was removed
        backup_path = adder.database_path.with_suffix(adder.database_path.suffix + ".backup")
        assert not backup_path.exists()

        # Verify can load saved database
        with open(adder.database_path, "rb") as f:
            loaded_databases = pickle.load(f)

        assert len(loaded_databases) == 2
        assert SupportedResolution.R_1080 in loaded_databases

    async def test_save_databases_creates_backup(self, adder: IconAdder) -> None:
        """Test that save_databases creates backup before saving.

        Args:
            adder (IconAdder): IconAdder instance from fixture.
        """
        adder.database_path.with_suffix(adder.database_path.suffix + ".backup")

        # Mock the write to fail after backup creation
        original_open = open

        def mock_open(*args: Any, **kwargs: Any) -> Any:
            path = str(args[0]) if args else ""
            if "wb" in args or kwargs.get("mode") == "wb":
                if not path.endswith(".backup"):
                    # Simulate failure during save
                    raise OSError("Simulated save failure")
            return original_open(*args, **kwargs)

        with patch("builtins.open", side_effect=mock_open):
            try:
                await adder.save_databases()
            except ValueError:
                pass  # Expected to fail

        # Original database should still exist (backup restored)
        assert adder.database_path.exists()


class TestMainFunction:
    """Test suite for the main CLI function.

    This class contains tests for the main entry point of the add icon
    command, including argument parsing and workflow execution.
    """

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.add_icon.add_icon.IconAdder")
    @patch("foxhole_stockpiles.commands.add_icon.add_icon.setup_logging")
    async def test_main_with_default_args(
        self,
        mock_setup_logging: Mock,
        mock_adder_class: Mock,
        mock_args: Mock,
        sample_database_file: Path,
        sample_icon_file: Path,
    ) -> None:
        """Test main function with default arguments.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_adder_class (Mock): Mocked IconAdder class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            sample_database_file (Path): Sample database file from fixture.
            sample_icon_file (Path): Sample icon file from fixture.
        """
        mock_args.return_value = argparse.Namespace(
            database=sample_database_file,
            icon=sample_icon_file,
            code="TestItem",
            faction="n",  # Use shorthand like inspector
            category="item",
            crated=False,
            mod="vanilla",
            resolution=["1080"],
            replace=False,
            verbose=False,
            quiet=False,
            log_file=None,
        )

        # Mock adder instance
        mock_adder = MagicMock()
        mock_adder.add_icon = AsyncMock(return_value=None)
        mock_adder.save_databases = AsyncMock(return_value=None)
        mock_adder_class.return_value = mock_adder

        await main()

        # Verify IconAdder was instantiated
        mock_adder_class.assert_called_once_with(database_path=sample_database_file)

        # Verify add_icon was called
        assert mock_adder.add_icon.call_count == 1

        # Verify save_databases was called
        mock_adder.save_databases.assert_called_once()

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.add_icon.add_icon.IconAdder")
    @patch("foxhole_stockpiles.commands.add_icon.add_icon.setup_logging")
    async def test_main_with_multiple_resolutions(
        self,
        mock_setup_logging: Mock,
        mock_adder_class: Mock,
        mock_args: Mock,
        sample_database_file: Path,
        sample_icon_file: Path,
    ) -> None:
        """Test main function with multiple resolution arguments.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_adder_class (Mock): Mocked IconAdder class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            sample_database_file (Path): Sample database file from fixture.
            sample_icon_file (Path): Sample icon file from fixture.
        """
        mock_args.return_value = argparse.Namespace(
            database=sample_database_file,
            icon=sample_icon_file,
            code="TestItem",
            faction="n",  # Use shorthand like inspector
            category="item",
            crated=False,
            mod="vanilla",
            resolution=["1080", "1440"],
            replace=False,
            verbose=False,
            quiet=False,
            log_file=None,
        )

        # Mock adder instance
        mock_adder = MagicMock()
        mock_adder.add_icon = AsyncMock(return_value=None)
        mock_adder.save_databases = AsyncMock(return_value=None)
        mock_adder_class.return_value = mock_adder

        await main()

        # Verify add_icon was called twice (once for each resolution)
        assert mock_adder.add_icon.call_count == 2

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.add_icon.add_icon.IconAdder")
    @patch("foxhole_stockpiles.commands.add_icon.add_icon.setup_logging")
    async def test_main_with_crated_flag(
        self,
        mock_setup_logging: Mock,
        mock_adder_class: Mock,
        mock_args: Mock,
        sample_database_file: Path,
        sample_icon_file: Path,
    ) -> None:
        """Test main function with crated flag.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_adder_class (Mock): Mocked IconAdder class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            sample_database_file (Path): Sample database file from fixture.
            sample_icon_file (Path): Sample icon file from fixture.
        """
        mock_args.return_value = argparse.Namespace(
            database=sample_database_file,
            icon=sample_icon_file,
            code="TestItem",
            faction="n",  # Use shorthand like inspector
            category="item",
            crated=True,  # Crated flag enabled
            mod="vanilla",
            resolution=["1080"],
            replace=False,
            verbose=False,
            quiet=False,
            log_file=None,
        )

        # Mock adder instance
        mock_adder = MagicMock()
        mock_adder.add_icon = AsyncMock(return_value=None)
        mock_adder.save_databases = AsyncMock(return_value=None)
        mock_adder_class.return_value = mock_adder

        await main()

        # Verify add_icon was called with crated=True
        call_kwargs = mock_adder.add_icon.call_args[1]
        assert call_kwargs["crated"] is True

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.add_icon.add_icon.IconAdder")
    @patch("foxhole_stockpiles.commands.add_icon.add_icon.setup_logging")
    async def test_main_with_verbose_mode(
        self,
        mock_setup_logging: Mock,
        mock_adder_class: Mock,
        mock_args: Mock,
        sample_database_file: Path,
        sample_icon_file: Path,
    ) -> None:
        """Test main function with verbose mode enabled.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_adder_class (Mock): Mocked IconAdder class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            sample_database_file (Path): Sample database file from fixture.
            sample_icon_file (Path): Sample icon file from fixture.
        """
        mock_args.return_value = argparse.Namespace(
            database=sample_database_file,
            icon=sample_icon_file,
            code="TestItem",
            faction="n",  # Use shorthand like inspector
            category="item",
            crated=False,
            mod="vanilla",
            resolution=["1080"],
            replace=False,
            verbose=True,  # Verbose mode
            quiet=False,
            log_file=None,
        )

        # Mock adder instance
        mock_adder = MagicMock()
        mock_adder.add_icon = AsyncMock(return_value=None)
        mock_adder.save_databases = AsyncMock(return_value=None)
        mock_adder_class.return_value = mock_adder

        await main()

        # Verify setup_logging was called
        mock_setup_logging.assert_called_once()

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.add_icon.add_icon.IconAdder")
    @patch("foxhole_stockpiles.commands.add_icon.add_icon.setup_logging")
    async def test_main_with_invalid_resolution(
        self,
        mock_setup_logging: Mock,
        mock_adder_class: Mock,
        mock_args: Mock,
        sample_database_file: Path,
        sample_icon_file: Path,
    ) -> None:
        """Test main function with invalid resolution argument.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_adder_class (Mock): Mocked IconAdder class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            sample_database_file (Path): Sample database file from fixture.
            sample_icon_file (Path): Sample icon file from fixture.
        """
        mock_args.return_value = argparse.Namespace(
            database=sample_database_file,
            icon=sample_icon_file,
            code="TestItem",
            faction="n",  # Use shorthand like inspector
            category="item",
            crated=False,
            mod="vanilla",
            resolution=["9999"],  # Invalid resolution
            verbose=False,
            quiet=False,
            log_file=None,
        )

        # Mock adder instance
        mock_adder = MagicMock()
        mock_adder.add_icon = AsyncMock(return_value=None)
        mock_adder.save_databases = AsyncMock(return_value=None)
        mock_adder_class.return_value = mock_adder

        # Should raise SystemExit due to parser.error()
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 2

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.add_icon.add_icon.IconAdder")
    @patch("foxhole_stockpiles.commands.add_icon.add_icon.setup_logging")
    async def test_main_with_different_factions(
        self,
        mock_setup_logging: Mock,
        mock_adder_class: Mock,
        mock_args: Mock,
        sample_database_file: Path,
        sample_icon_file: Path,
    ) -> None:
        """Test main function with different faction values.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_adder_class (Mock): Mocked IconAdder class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            sample_database_file (Path): Sample database file from fixture.
            sample_icon_file (Path): Sample icon file from fixture.
        """
        # ItemFaction.from_string converts shorthand to proper enum values
        expected_faction_values = {
            "c": "Colonials",
            "w": "Wardens",
            "n": "neutral",
        }

        for faction in ["c", "w", "n"]:
            # Reset mock for each iteration
            mock_adder_class.reset_mock()

            mock_args.return_value = argparse.Namespace(
                database=sample_database_file,
                icon=sample_icon_file,
                code="TestItem",
                faction=faction,
                category="item",
                crated=False,
                mod="vanilla",
                resolution=["1080"],
                replace=False,
                verbose=False,
                quiet=False,
                log_file=None,
            )

            # Mock adder instance
            mock_adder = MagicMock()
            mock_adder.add_icon = AsyncMock(return_value=None)
            mock_adder.save_databases = AsyncMock(return_value=None)
            mock_adder_class.return_value = mock_adder

            await main()

            # Verify add_icon was called with correct faction
            call_kwargs = mock_adder.add_icon.call_args[1]
            assert call_kwargs["faction"].value == expected_faction_values[faction]
