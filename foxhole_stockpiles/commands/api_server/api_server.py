"""API server command for running the FastAPI application."""

import argparse
import sys

import uvicorn

from foxhole_stockpiles.core.settings import get_settings


def main() -> int:
    """Run the API server.

    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    # Load settings to get defaults
    settings = get_settings()

    parser = argparse.ArgumentParser(
        description="Start the Foxhole Stockpile Scanner API server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help=f"Bind socket to this host (default: {settings.api_server.host})",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=f"Bind socket to this port (default: {settings.api_server.port})",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help=f"Number of worker processes (default: {settings.api_server.workers})",
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        default=None,
        help="Enable auto-reload on code changes (development only)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default=None,
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help=f"Log level (default: {settings.api_server.log_level})",
    )

    args = parser.parse_args()

    # Use CLI args if provided, otherwise fall back to settings
    host = args.host if args.host is not None else settings.api_server.host
    port = args.port if args.port is not None else settings.api_server.port
    workers = args.workers if args.workers is not None else settings.api_server.workers
    reload = args.reload if args.reload is not None else settings.api_server.reload
    log_level = args.log_level if args.log_level is not None else settings.api_server.log_level

    try:
        uvicorn.run(
            "foxhole_stockpiles.api.server:app",
            host=host,
            port=port,
            workers=workers,
            reload=reload,
            log_level=log_level,
        )
        return 0
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
