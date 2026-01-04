"""Server thread for running FastAPI server in background."""

import logging
import threading

import uvicorn

from foxhole_stockpiles.core.settings import get_settings

logger = logging.getLogger(__name__)


class ServerThread(threading.Thread):
    """Thread for running the FastAPI server."""

    def __init__(self) -> None:
        """Initialize the server thread."""
        super().__init__(daemon=True)
        self.server: uvicorn.Server | None = None
        self._stop_event = threading.Event()

    def run(self) -> None:
        """Run the FastAPI server."""
        settings = get_settings()

        try:
            logger.info("Starting FastAPI server...")
            logger.info(
                "Server will be available at http://%s:%s",
                settings.api_server.host,
                settings.api_server.port,
            )

            # Create uvicorn config
            config = uvicorn.Config(
                "foxhole_stockpiles.api.server:app",
                host=settings.api_server.host,
                port=settings.api_server.port,
                workers=1,  # Force single worker for thread safety
                reload=False,  # Disable reload in GUI mode
                log_level=settings.api_server.log_level,
            )

            # Create and run server
            self.server = uvicorn.Server(config)
            self.server.run()

        except Exception as e:
            logger.error("Server error: %s", e, exc_info=True)

    def stop(self) -> None:
        """Stop the server."""
        if self.server:
            logger.info("Shutting down server...")
            self.server.should_exit = True
            self._stop_event.set()
