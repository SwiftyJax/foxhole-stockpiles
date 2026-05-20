"""GUI command for launching the PySide6 application."""

from foxhole_stockpiles.gui.app import launch_gui


async def main() -> None:
    """Entry point for GUI command."""
    launch_gui()
