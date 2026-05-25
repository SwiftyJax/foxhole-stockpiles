"""``fs serve`` — start the FastAPI server."""

import typer
import uvicorn

from foxhole_stockpiles.core.settings import get_settings

app = typer.Typer(help="Start the API server.")

_LOG_LEVELS = ["critical", "error", "warning", "info", "debug", "trace"]


@app.callback(invoke_without_command=True)
def serve(
    host: str | None = typer.Option(None, "--host", help="Bind socket to this host."),
    port: int | None = typer.Option(None, "--port", help="Bind socket to this port."),
    workers: int | None = typer.Option(None, "--workers", help="Number of worker processes."),
    reload: bool = typer.Option(
        False, "--reload", help="Enable auto-reload on code changes (development only)."
    ),
    log_level: str | None = typer.Option(
        None,
        "--log-level",
        help=f"Log level. One of: {', '.join(_LOG_LEVELS)}.",
    ),
) -> None:
    """Start the Foxhole Stockpile Scanner API server.

    Args:
        host (str | None): Host to bind. Falls back to configured value.
        port (int | None): Port to bind. Falls back to configured value.
        workers (int | None): Worker process count. Falls back to configured value.
        reload (bool): Enable uvicorn auto-reload (development only).
        log_level (str | None): Uvicorn log level. Falls back to configured value.

    Raises:
        typer.Exit: If an invalid log level is given or the server fails to start.
    """
    if log_level is not None and log_level not in _LOG_LEVELS:
        typer.echo(f"Error: invalid log level '{log_level}'", err=True)
        raise typer.Exit(code=2)

    settings = get_settings()

    resolved_host = host if host is not None else settings.api_server.host
    resolved_port = port if port is not None else settings.api_server.port
    resolved_workers = workers if workers is not None else settings.api_server.workers
    resolved_reload = reload if reload else settings.api_server.reload
    resolved_log_level = log_level if log_level is not None else settings.api_server.log_level

    try:
        uvicorn.run(
            "foxhole_stockpiles.api.server:app",
            host=resolved_host,
            port=resolved_port,
            workers=resolved_workers,
            reload=resolved_reload,
            log_level=resolved_log_level,
        )
    except Exception as e:  # noqa: BLE001 - surface any startup failure as exit code 1
        typer.echo(f"Error starting server: {e}", err=True)
        raise typer.Exit(code=1) from e
