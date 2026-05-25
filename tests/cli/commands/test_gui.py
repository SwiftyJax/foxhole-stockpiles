"""Tests for the ``fs gui`` command (``foxhole_stockpiles.cli.commands.gui``)."""

from unittest.mock import patch

from typer.testing import CliRunner

from foxhole_stockpiles.cli.commands import gui

runner = CliRunner()


class TestGuiCommand:
    """Test suite for the ``gui`` command via CliRunner."""

    def test_launches_gui(self) -> None:
        """Invoking the command launches the PySide6 GUI."""
        with patch("foxhole_stockpiles.cli.commands.gui.launch_gui") as mock_launch:
            result = runner.invoke(gui.app, [])

            assert result.exit_code == 0
            mock_launch.assert_called_once()
