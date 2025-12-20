"""Memory monitoring middleware for FastAPI."""

import gc
import time
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from foxhole_stockpiles.core.utils import malloc_trim
from foxhole_stockpiles.services.memory_monitor import MemoryMonitor


class MemoryMonitorMiddleware(BaseHTTPMiddleware):
    """Middleware to track memory usage per request and optionally auto-trim memory."""

    def __init__(
        self,
        app: Any,
        monitor: MemoryMonitor,
        auto_trim_after_scan: bool = True,
        enable_monitoring: bool = True,
    ) -> None:
        """Initialize middleware.

        Args:
            app: FastAPI application
            monitor: MemoryMonitor instance
            auto_trim_after_scan: If True, automatically call malloc_trim() after scan requests
                to release memory back to OS (default: True)
            enable_monitoring: If True, track memory statistics and snapshots (default: True)
        """
        super().__init__(app)
        self.monitor = monitor
        self.auto_trim_after_scan = auto_trim_after_scan
        self.enable_monitoring = enable_monitoring

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request and optionally track memory.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response: FastAPI response
        """
        # Skip middleware for memory endpoints
        if request.url.path.startswith("/memory"):
            return await call_next(request)

        # Only do monitoring work if enabled
        if self.enable_monitoring:
            # Get memory before request
            memory_before = self.monitor.get_current_memory()
            start_time = time.perf_counter()

            # Process request
            response = await call_next(request)

            # Get memory after request
            duration_ms = (time.perf_counter() - start_time) * 1000
            memory_after = self.monitor.get_current_memory()

            # Record statistics
            self.monitor.request_count += 1
            self.monitor.record_request(
                path=request.url.path,
                method=request.method,
                duration_ms=duration_ms,
                memory_before_mb=memory_before.rss_mb,
                memory_after_mb=memory_after.rss_mb,
                status_code=response.status_code,
            )

            # Take periodic snapshots
            if self.monitor.request_count % self.monitor.snapshot_interval == 0:
                self.monitor._take_snapshot()
        else:
            # No monitoring, just process the request
            response = await call_next(request)

        # Auto-trim memory after scan requests (independent of monitoring)
        if self.auto_trim_after_scan and request.url.path == "/ocr/scan_image":
            gc.collect()
            malloc_trim()

        return response
