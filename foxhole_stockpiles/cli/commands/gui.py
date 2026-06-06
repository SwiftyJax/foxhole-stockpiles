"""``fs gui`` — launch the PySide6 desktop application."""

import typer

from foxhole_stockpiles.gui.app import launch_gui

app = typer.Typer(help="Launch the GUI application.")


@app.callback(invoke_without_command=True)
def gui() -> None:
    """Launch the PySide6 GUI application."""
    launch_gui()
