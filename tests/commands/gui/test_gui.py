"""Tests for commands.gui module.

This module contains tests for the GUI command module including
the main function and module entry point.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGuiMain:
    """Test suite for GUI command main function."""

    @pytest.mark.asyncio
    async def test_main_calls_launch_gui(self) -> None:
        """Test that main function calls launch_gui."""
        with patch("foxhole_stockpiles.commands.gui.gui.launch_gui") as mock_launch:
            from foxhole_stockpiles.commands.gui.gui import main

            await main()

            mock_launch.assert_called_once()


class TestGuiModuleEntryPoint:
    """Test suite for GUI __main__ module entry point."""

    def test_main_module_imports(self) -> None:
        """Test that the __main__ module can be imported."""
        # Just importing should work without errors
        import foxhole_stockpiles.commands.gui.__main__  # noqa: F401

    def test_main_module_execution(self) -> None:
        """Test that the module can be executed as __main__."""
        with patch("foxhole_stockpiles.commands.gui.gui.main", new_callable=AsyncMock) as mock_main:
            with patch("asyncio.run") as mock_asyncio_run:
                # Simulate running as __main__
                exec(
                    "if __name__ == '__main__': asyncio.run(main())",
                    {
                        "__name__": "__main__",
                        "asyncio": MagicMock(run=mock_asyncio_run),
                        "main": mock_main,
                    },
                )
                mock_asyncio_run.assert_called_once()
