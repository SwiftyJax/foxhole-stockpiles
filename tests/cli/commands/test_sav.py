"""Tests for the ``fs sav`` command (``foxhole_stockpiles.cli.commands.sav``)."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from foxhole_stockpiles.cli.commands import sav

runner = CliRunner()


class TestFindMapdataFile:
    """Test suite for the ``_find_mapdata_file`` helper."""

    def test_finds_mapdata_file(self, tmp_path: Path) -> None:
        """Returns the MapData.sav file present in the directory.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        save_file = tmp_path / "World_MapData.sav"
        save_file.touch()

        assert sav._find_mapdata_file(tmp_path) == save_file

    def test_returns_none_when_absent(self, tmp_path: Path) -> None:
        """Returns None when no MapData.sav file is present.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        assert sav._find_mapdata_file(tmp_path) is None


class TestResolveSaveFile:
    """Test suite for the ``_resolve_save_file`` helper."""

    def test_explicit_file(self, tmp_path: Path) -> None:
        """An explicit, existing file is returned unchanged.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        save_file = tmp_path / "World_MapData.sav"
        save_file.touch()

        assert sav._resolve_save_file(save_file, None) == save_file

    def test_save_dir_lookup(self, tmp_path: Path) -> None:
        """A save directory is searched for a MapData.sav file.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        save_file = tmp_path / "World_MapData.sav"
        save_file.touch()

        assert sav._resolve_save_file(None, tmp_path) == save_file


class TestSavCommand:
    """Test suite for the ``sav`` command via CliRunner."""

    def test_no_file_found_exits_one(self, tmp_path: Path) -> None:
        """No discoverable save file exits with code 1.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        result = runner.invoke(sav.app, ["--save-dir", str(tmp_path)])

        assert result.exit_code == 1

    def test_missing_explicit_file_exits_one(self, tmp_path: Path) -> None:
        """An explicit file that does not exist exits with code 1.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        result = runner.invoke(sav.app, ["--file", str(tmp_path / "missing.sav")])

        assert result.exit_code == 1

    @patch("foxhole_stockpiles.cli.commands.sav.SaveFileProcessor")
    @patch("foxhole_stockpiles.cli.commands.sav.OutputCoordinator")
    @patch("foxhole_stockpiles.cli.commands.sav.setup_logging")
    def test_once_processes_and_exits(
        self,
        mock_setup_logging: MagicMock,
        mock_output_coordinator: MagicMock,
        mock_processor_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """``--once`` runs the processor a single time.

        Args:
            mock_setup_logging (MagicMock): Mocked setup_logging.
            mock_output_coordinator (MagicMock): Mocked OutputCoordinator.
            mock_processor_class (MagicMock): Mocked SaveFileProcessor.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        save_file = tmp_path / "World_MapData.sav"
        save_file.touch()

        processor = MagicMock()
        processor.run_once = AsyncMock(return_value=None)
        mock_processor_class.return_value = processor

        result = runner.invoke(sav.app, ["--file", str(save_file), "--once"])

        assert result.exit_code == 0
        processor.run_once.assert_awaited_once()
