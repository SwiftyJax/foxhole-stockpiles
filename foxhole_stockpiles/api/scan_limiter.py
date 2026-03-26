"""Scan concurrency limiter for CPU-bound operations.

This module provides concurrency limiting for scan operations to prevent
CPU contention when multiple requests arrive simultaneously.
"""

import asyncio
import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScanLimiterStats:
    """Statistics for scan limiter usage."""

    total_scans: int = 0
    queued_scans: int = 0
    total_queue_wait_ms: float = 0
    max_queue_wait_ms: float = 0
    current_active: int = 0
    current_waiting: int = 0

    @property
    def avg_queue_wait_ms(self) -> float:
        """Average queue wait time in milliseconds.

        Returns:
            float: Average wait time, or 0 if no queued scans.
        """
        if self.queued_scans == 0:
            return 0
        return self.total_queue_wait_ms / self.queued_scans


class ScanLimiter:
    """Semaphore-based limiter for concurrent scan operations.

    Limits the number of concurrent CPU-intensive scan operations to prevent
    CPU contention and maintain consistent response times.

    Note: This is a per-worker limiter. With multiple uvicorn workers,
    effective concurrency = workers * max_concurrent_scans.
    For a 6-core VPS, recommended: workers=2, max_concurrent_scans=2
    (effective max = 4, leaving headroom for other processes).
    """

    def __init__(self, max_concurrent: int = 0) -> None:
        """Initialize the scan limiter.

        Args:
            max_concurrent (int): Maximum concurrent scans per worker.
                Set to 0 to disable limiting.
        """
        self._max_concurrent = max_concurrent
        self._semaphore: asyncio.Semaphore | None = None
        self._stats = ScanLimiterStats()
        self._lock = asyncio.Lock()

        if max_concurrent > 0:
            self._semaphore = asyncio.Semaphore(max_concurrent)
            logger.info(
                "Scan limiter initialized: max %d concurrent scans per worker",
                max_concurrent,
            )
        else:
            logger.info("Scan limiter disabled (max_concurrent_scans=0)")

    @property
    def max_concurrent(self) -> int:
        """Get the maximum concurrent scans limit.

        Returns:
            int: Maximum concurrent scans (0 = unlimited).
        """
        return self._max_concurrent

    @property
    def is_enabled(self) -> bool:
        """Check if limiting is enabled.

        Returns:
            bool: True if limiting is enabled.
        """
        return self._semaphore is not None

    def get_stats(self) -> dict[str, float | int]:
        """Get limiter statistics.

        Returns:
            dict[str, float | int]: Statistics dictionary.
        """
        return {
            "max_concurrent": self._max_concurrent,
            "enabled": self.is_enabled,
            "total_scans": self._stats.total_scans,
            "queued_scans": self._stats.queued_scans,
            "avg_queue_wait_ms": round(self._stats.avg_queue_wait_ms, 2),
            "max_queue_wait_ms": round(self._stats.max_queue_wait_ms, 2),
            "current_active": self._stats.current_active,
            "current_waiting": self._stats.current_waiting,
        }

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[None, None]:
        """Acquire a slot for a scan operation.

        This is an async context manager that waits for an available slot
        if all slots are currently in use.

        Yields:
            None: Control to the caller while slot is held.

        Example:
            async with scan_limiter.acquire():
                result = await do_scan(image)
        """
        if self._semaphore is None:
            # Limiting disabled
            self._stats.total_scans += 1
            yield
            return

        # Check if we need to wait
        start_time = time.perf_counter()
        needs_wait = self._semaphore.locked()

        if needs_wait:
            async with self._lock:
                self._stats.current_waiting += 1
            logger.debug("Scan queued, waiting for available slot...")

        try:
            await self._semaphore.acquire()

            # Update stats
            async with self._lock:
                self._stats.total_scans += 1
                self._stats.current_active += 1
                if needs_wait:
                    self._stats.current_waiting -= 1
                    wait_ms = (time.perf_counter() - start_time) * 1000
                    self._stats.queued_scans += 1
                    self._stats.total_queue_wait_ms += wait_ms
                    self._stats.max_queue_wait_ms = max(self._stats.max_queue_wait_ms, wait_ms)
                    logger.debug("Scan slot acquired after %.1fms wait", wait_ms)

            yield

        finally:
            self._semaphore.release()
            async with self._lock:
                self._stats.current_active -= 1
