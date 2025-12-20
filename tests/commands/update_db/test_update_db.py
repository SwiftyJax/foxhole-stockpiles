"""Tests for update-db command module.

This module contains comprehensive tests for the update-db command,
including successful updates, error handling, and various edge cases.
"""

import logging
import pickle
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import patch

import h5py
import numpy as np
import pytest

from foxhole_stockpiles.commands.update_db.update_db import main
from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.models.icon_template import IconTemplate
from foxhole_stockpiles.services.template_database import DATABASE_VERSION, TemplateDatabase


def test_main_module_importable() -> None:
    """Test that __main__ module can be imported without errors."""
    import foxhole_stockpiles.commands.update_db.__main__  # noqa: F401


def create_v1_pickle_database(db_path: Path) -> None:
    """Create a v1 pickle database for testing.

    Args:
        db_path (Path): Path where the pickle database will be created.
    """
    # Create sample template databases for different resolutions
    databases = {}

    for resolution in [SupportedResolution.R_1080, SupportedResolution.R_1440]:
        db = TemplateDatabase(resolution=resolution)

        # Add a few sample templates
        for i in range(3):
            # Create a simple test image
            image = np.zeros((32, 32, 3), dtype=np.uint8)
            image[:, :] = [100 + i * 20, 100 + i * 20, 100 + i * 20]

            template = IconTemplate(
                image=image,
                code=f"TestItem{i}",
                crated=(i % 2 == 0),
                resolution=resolution,
                faction=ItemFaction.NEUTRAL if i == 0 else ItemFaction.COLONIALS,
                category=ItemCategory.Item,
                mod="vanilla",
            )
            db.add_template(template)

        databases[resolution] = db

    # Save as pickle
    with open(db_path, "wb") as f:
        pickle.dump(databases, f)


def create_v2_hdf5_database(db_path: Path) -> None:
    """Create a v2 HDF5 database for testing.

    Args:
        db_path (Path): Path where the HDF5 database will be created.
    """
    # Create sample template databases
    databases = {}

    for resolution in [SupportedResolution.R_1080, SupportedResolution.R_1440]:
        db = TemplateDatabase(resolution=resolution)

        # Add a few sample templates
        for i in range(3):
            image = np.zeros((32, 32, 3), dtype=np.uint8)
            image[:, :] = [100 + i * 20, 100 + i * 20, 100 + i * 20]

            template = IconTemplate(
                image=image,
                code=f"TestItem{i}",
                crated=(i % 2 == 0),
                resolution=resolution,
                faction=ItemFaction.NEUTRAL if i == 0 else ItemFaction.COLONIALS,
                category=ItemCategory.Item,
                mod="vanilla",
            )
            db.add_template(template)

        databases[resolution] = db

    # Save as HDF5
    with h5py.File(str(db_path), "w") as f:
        # Set root-level attributes
        f.attrs["version"] = DATABASE_VERSION
        f.attrs["format"] = "hdf5"
        f.attrs["resolutions"] = [res.value for res in databases.keys()]

        # Save each resolution's database
        for resolution, db in databases.items():
            group = f.create_group(resolution.value)
            db.save_to_hdf5_group(group)


class TestUpdateDbCommand:
    """Test cases for update-db command."""

    @pytest.mark.asyncio
    async def test_update_v1_to_v2_success(
        self, tmp_path: Path, test_db_v1_fixture: Path, caplog: Any
    ) -> None:
        """Test successful update from v1 (pickle) to v2 (HDF5).

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
            test_db_v1_fixture (Path): Path to v1 test database fixture.
            caplog: Pytest fixture to capture log messages.
        """
        # Configure caplog to capture at INFO level
        caplog.set_level(logging.INFO)

        # Copy fixture to tmp_path for test isolation
        db_path = tmp_path / "templates.pkl"
        shutil.copy2(test_db_v1_fixture, db_path)

        # Run update command, mock setup_logging to prevent it from overriding caplog
        with patch("sys.argv", ["update-db", "--database-path", str(db_path)]):
            with patch("foxhole_stockpiles.commands.update_db.update_db.setup_logging"):
                result = await main()

        # Verify command succeeded
        assert result == 0

        # Verify output was created
        output_path = db_path.with_suffix(".h5")
        assert output_path.exists()

        # Verify it's a valid HDF5 file with correct version
        with h5py.File(str(output_path), "r") as f:
            assert f.attrs["version"] == DATABASE_VERSION
            assert f.attrs["format"] == "hdf5"
            assert "1080" in f
            assert "1440" in f

        # Verify log messages
        assert "Migration completed successfully!" in caplog.text
        assert "Saved 2 templates" in caplog.text
        assert "/1080" in caplog.text
        assert "/1440" in caplog.text

    @pytest.mark.asyncio
    async def test_already_at_latest_version(self, tmp_path: Path, caplog: Any) -> None:
        """Test when database is already at latest version.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
            caplog: Pytest fixture to capture log messages.
        """
        # Configure caplog to capture at INFO level
        caplog.set_level(logging.INFO)

        # Create v2 HDF5 database
        db_path = tmp_path / "templates.h5"
        create_v2_hdf5_database(db_path)

        # Run update command
        with patch("sys.argv", ["update-db", "--database-path", str(db_path)]):
            with patch("foxhole_stockpiles.commands.update_db.update_db.setup_logging"):
                result = await main()

        # Verify command succeeded with no changes
        assert result == 0

        # Verify log messages
        assert "already at current version" in caplog.text
        assert "No migrations needed" in caplog.text

    @pytest.mark.asyncio
    async def test_database_file_not_found(self, tmp_path: Path, caplog: Any) -> None:
        """Test when database file doesn't exist.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
            caplog: Pytest fixture to capture log messages.
        """
        # Configure caplog to capture at INFO level
        caplog.set_level(logging.INFO)

        # Point to non-existent file
        db_path = tmp_path / "nonexistent.pkl"

        # Run update command
        with patch("sys.argv", ["update-db", "--database-path", str(db_path)]):
            with patch("foxhole_stockpiles.commands.update_db.update_db.setup_logging"):
                result = await main()

        # Verify command failed
        assert result == 1

        # Verify log messages
        assert "Database file not found" in caplog.text
        assert "Nothing to migrate" in caplog.text

    @pytest.mark.asyncio
    async def test_invalid_database_file(self, tmp_path: Path, caplog: Any) -> None:
        """Test when database file is corrupted or invalid.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
            caplog: Pytest fixture to capture log messages.
        """
        # Configure caplog to capture at INFO level
        caplog.set_level(logging.INFO)

        # Create file with invalid content
        db_path = tmp_path / "corrupted.pkl"
        db_path.write_bytes(b"not a valid database file")

        # Run update command
        with patch("sys.argv", ["update-db", "--database-path", str(db_path)]):
            with patch("foxhole_stockpiles.commands.update_db.update_db.setup_logging"):
                result = await main()

        # Verify command failed
        assert result == 1

        # Verify log message
        assert "corrupted or in an unrecognized format" in caplog.text

    @pytest.mark.asyncio
    async def test_custom_output_path(self, tmp_path: Path, test_db_v1_fixture: Path) -> None:
        """Test using custom output path.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
            test_db_v1_fixture (Path): Path to v1 test database fixture.
        """
        # Copy fixture to tmp_path
        db_path = tmp_path / "templates.pkl"
        shutil.copy2(test_db_v1_fixture, db_path)

        # Custom output path
        custom_output = tmp_path / "migrated_database.h5"

        # Run update command with custom output
        with patch(
            "sys.argv",
            ["update-db", "--database-path", str(db_path), "--output", str(custom_output)],
        ):
            result = await main()

        # Verify command succeeded
        assert result == 0

        # Verify custom output was created
        assert custom_output.exists()

        # Verify it's valid HDF5
        with h5py.File(str(custom_output), "r") as f:
            assert f.attrs["version"] == DATABASE_VERSION

    @pytest.mark.asyncio
    async def test_migration_error(
        self, tmp_path: Path, test_db_v1_fixture: Path, caplog: Any
    ) -> None:
        """Test error handling during migration process.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
            test_db_v1_fixture (Path): Path to v1 test database fixture.
            caplog: Pytest fixture to capture log messages.
        """
        # Configure caplog to capture at INFO level
        caplog.set_level(logging.INFO)

        # Copy fixture to tmp_path
        db_path = tmp_path / "templates.pkl"
        shutil.copy2(test_db_v1_fixture, db_path)

        # Mock migrate_database to raise exception
        with patch(
            "foxhole_stockpiles.commands.update_db.update_db.TemplateManager.migrate_database",
            side_effect=ValueError("Migration failed"),
        ):
            with patch("sys.argv", ["update-db", "--database-path", str(db_path)]):
                with patch("foxhole_stockpiles.commands.update_db.update_db.setup_logging"):
                    result = await main()

        # Verify command failed
        assert result == 1

        # Verify error message
        assert "Migration failed" in caplog.text

    @pytest.mark.asyncio
    async def test_verbose_logging(
        self, tmp_path: Path, test_db_v1_fixture: Path, caplog: Any
    ) -> None:
        """Test verbose logging mode.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
            test_db_v1_fixture (Path): Path to v1 test database fixture.
            caplog: Pytest fixture to capture log messages.
        """
        # Configure caplog to capture at INFO level
        caplog.set_level(logging.INFO)

        # Copy fixture to tmp_path
        db_path = tmp_path / "templates.pkl"
        shutil.copy2(test_db_v1_fixture, db_path)

        # Run update command with --verbose
        with patch("sys.argv", ["update-db", "--database-path", str(db_path), "--verbose"]):
            with patch("foxhole_stockpiles.commands.update_db.update_db.setup_logging"):
                result = await main()

        # Verify command succeeded
        assert result == 0

        # Verbose mode enables debug logging - check for migration messages
        assert "Applying migration: v1 → v2" in caplog.text

    @pytest.mark.asyncio
    async def test_quiet_mode(self, tmp_path: Path, caplog: Any) -> None:
        """Test quiet mode suppresses normal output.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
            caplog: Pytest fixture to capture log messages.
        """
        # Configure caplog to capture at WARNING level for quiet mode
        caplog.set_level(logging.WARNING)

        # Create v2 HDF5 database (no migration needed)
        db_path = tmp_path / "templates.h5"
        create_v2_hdf5_database(db_path)

        # Run update command with --quiet
        # Mock setup_logging and manually set logger to WARNING level
        def mock_setup_logging(_: Any) -> None:
            logging.getLogger("foxhole_stockpiles.commands.update_db.update_db").setLevel(
                logging.WARNING
            )

        with patch("sys.argv", ["update-db", "--database-path", str(db_path), "--quiet"]):
            with patch(
                "foxhole_stockpiles.commands.update_db.update_db.setup_logging",
                side_effect=mock_setup_logging,
            ):
                result = await main()

        # Verify command succeeded
        assert result == 0

        # Quiet mode should suppress info messages
        # In quiet mode, only warnings and errors should appear
        # Since database is up-to-date, there should be minimal log output
        # Check that INFO level messages are not present
        assert len([r for r in caplog.records if r.levelname == "INFO"]) == 0


class TestUpdateDbEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_empty_pickle_database(self, tmp_path: Path) -> None:
        """Test migration of empty pickle database.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
        """
        # Create empty pickle database
        db_path = tmp_path / "empty.pkl"
        databases = {
            SupportedResolution.R_1080: TemplateDatabase(SupportedResolution.R_1080),
            SupportedResolution.R_1440: TemplateDatabase(SupportedResolution.R_1440),
        }

        with open(db_path, "wb") as f:
            pickle.dump(databases, f)

        # Run update command
        with patch("sys.argv", ["update-db", "--database-path", str(db_path)]):
            with patch("foxhole_stockpiles.commands.update_db.update_db.setup_logging"):
                result = await main()

        # Verify command succeeded
        assert result == 0

        # Verify output exists
        output_path = db_path.with_suffix(".h5")
        assert output_path.exists()

    @pytest.mark.asyncio
    async def test_single_resolution_database(self, tmp_path: Path) -> None:
        """Test migration of database with only one resolution.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
        """
        # Create database with single resolution
        db_path = tmp_path / "single_res.pkl"
        db = TemplateDatabase(SupportedResolution.R_1080)

        # Add one template
        image = np.zeros((32, 32, 3), dtype=np.uint8)
        template = IconTemplate(
            image=image,
            code="TestItem",
            crated=False,
            resolution=SupportedResolution.R_1080,
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            mod="vanilla",
        )
        db.add_template(template)

        databases = {SupportedResolution.R_1080: db}

        with open(db_path, "wb") as f:
            pickle.dump(databases, f)

        # Run update command
        with patch("sys.argv", ["update-db", "--database-path", str(db_path)]):
            with patch("foxhole_stockpiles.commands.update_db.update_db.setup_logging"):
                result = await main()

        # Verify command succeeded
        assert result == 0

        # Verify output exists and has correct structure
        output_path = db_path.with_suffix(".h5")
        with h5py.File(str(output_path), "r") as f:
            assert "1080" in f
            assert f["1080"].attrs["template_count"] == 1

    @pytest.mark.asyncio
    async def test_no_database_path_configured(self, tmp_path: Path, caplog: Any) -> None:
        """Test when no database path is configured and none provided.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
            caplog: Pytest fixture to capture log messages.
        """
        # Configure caplog to capture at INFO level
        caplog.set_level(logging.INFO)

        # Mock get_settings to return settings without database_path
        from unittest.mock import MagicMock

        with patch(
            "foxhole_stockpiles.commands.update_db.update_db.get_settings"
        ) as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.scanner.database_path = None
            mock_settings.logging.log_level = "INFO"
            mock_settings.logging.log_file = None
            mock_settings.logging.log_format = (
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            mock_settings.logging.date_format = "%Y-%m-%d %H:%M:%S"
            mock_get_settings.return_value = mock_settings

            # Run update command without --database-path
            with patch("sys.argv", ["update-db"]):
                with patch("foxhole_stockpiles.commands.update_db.update_db.setup_logging"):
                    result = await main()

        # Verify command failed
        assert result == 1

        # Verify error message
        assert "No database path configured" in caplog.text

    @pytest.mark.asyncio
    async def test_preserves_template_data(self, tmp_path: Path) -> None:
        """Test that migration preserves all template data correctly.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
        """
        # Create v1 pickle database with specific data
        db_path = tmp_path / "templates.pkl"
        db = TemplateDatabase(SupportedResolution.R_1080)

        # Add template with specific values
        image = np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8)
        template = IconTemplate(
            image=image,
            code="SpecificItem",
            crated=True,
            resolution=SupportedResolution.R_1080,
            faction=ItemFaction.WARDENS,
            category=ItemCategory.Vehicle,
            mod="test_mod",
        )
        db.add_template(template)

        databases = {SupportedResolution.R_1080: db}
        with open(db_path, "wb") as f:
            pickle.dump(databases, f)

        # Run migration
        with patch("sys.argv", ["update-db", "--database-path", str(db_path)]):
            with patch("foxhole_stockpiles.commands.update_db.update_db.setup_logging"):
                result = await main()

        assert result == 0

        # Load migrated database and verify data
        output_path = db_path.with_suffix(".h5")
        from foxhole_stockpiles.services.template_manager import TemplateManager

        manager = TemplateManager(database_path=output_path)
        migrated_db = await manager.load_database(SupportedResolution.R_1080)

        assert len(migrated_db.templates) == 1
        migrated_template = migrated_db.templates[0]
        assert migrated_template.code == "SpecificItem"
        assert migrated_template.crated is True
        assert migrated_template.faction == ItemFaction.WARDENS
        assert migrated_template.category == ItemCategory.Vehicle
        assert migrated_template.mod == "test_mod"
        assert np.array_equal(migrated_template.image, image)


class TestMultiprocessingMigration:
    """Test multiprocessing functionality in migrations."""

    async def test_migration_with_workers(self, tmp_path: Path) -> None:
        """Test migration with multiple workers.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
        """
        # Create v1 pickle database with multiple resolutions
        db_path = tmp_path / "templates.pkl"
        create_v1_pickle_database(db_path)

        # Run migration with 2 workers
        with patch("sys.argv", ["update-db", "--database-path", str(db_path), "--workers", "2"]):
            with patch("foxhole_stockpiles.commands.update_db.update_db.setup_logging"):
                result = await main()

        assert result == 0

        # Verify output file exists
        output_path = db_path.with_suffix(".h5")
        assert output_path.exists()

        # Verify database can be loaded and has correct data
        from foxhole_stockpiles.services.template_manager import TemplateManager

        manager = TemplateManager(database_path=output_path)

        # Check both resolutions
        for resolution in [SupportedResolution.R_1080, SupportedResolution.R_1440]:
            db = await manager.load_database(resolution)
            assert len(db.templates) == 3

    async def test_migration_with_single_worker(self, tmp_path: Path) -> None:
        """Test migration with single worker (no multiprocessing).

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
        """
        # Create v1 pickle database
        db_path = tmp_path / "templates.pkl"
        create_v1_pickle_database(db_path)

        # Run migration with 1 worker (disables multiprocessing)
        with patch("sys.argv", ["update-db", "--database-path", str(db_path), "--workers", "1"]):
            with patch("foxhole_stockpiles.commands.update_db.update_db.setup_logging"):
                result = await main()

        assert result == 0

        # Verify output file exists
        output_path = db_path.with_suffix(".h5")
        assert output_path.exists()

    async def test_migration_multiprocessing_vs_single_thread(self, tmp_path: Path) -> None:
        """Test that multiprocessing and single-threaded produce same results.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
        """
        # Create v1 pickle database
        db_path = tmp_path / "templates.pkl"
        create_v1_pickle_database(db_path)

        # Create two output paths
        output_multi = tmp_path / "multi.h5"
        output_single = tmp_path / "single.h5"

        from foxhole_stockpiles.services.template_manager import TemplateManager

        # Load pickle database
        with open(db_path, "rb") as f:
            all_databases = pickle.load(f)

        # Save with multiprocessing
        TemplateManager.save_databases_to_hdf5(all_databases, output_multi, workers=2)

        # Save without multiprocessing
        TemplateManager.save_databases_to_hdf5(all_databases, output_single, workers=1)

        # Load both and compare
        manager_multi = TemplateManager(database_path=output_multi)
        manager_single = TemplateManager(database_path=output_single)

        for resolution in [SupportedResolution.R_1080, SupportedResolution.R_1440]:
            db_multi = await manager_multi.load_database(resolution)
            db_single = await manager_single.load_database(resolution)

            # Should have same number of templates
            assert len(db_multi.templates) == len(db_single.templates)

            # Compare each template
            for t1, t2 in zip(db_multi.templates, db_single.templates, strict=True):
                assert t1.code == t2.code
                assert t1.crated == t2.crated
                assert t1.faction == t2.faction
                assert t1.category == t2.category
                assert t1.mod == t2.mod
                assert np.array_equal(t1.image, t2.image)
