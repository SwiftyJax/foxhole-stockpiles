"""Memory monitoring service for tracking memory usage and detecting leaks."""

import logging
from collections import deque
from datetime import datetime
from typing import Any

import psutil

from foxhole_stockpiles.core.utils import force_memory_release
from foxhole_stockpiles.models.memory_snapshot import MemorySnapshot
from foxhole_stockpiles.models.request_memory_stats import RequestMemoryStats


class MemoryMonitor:
    """Tracks memory usage over time and per-request."""

    def __init__(self, history_size: int = 1000, snapshot_interval: int = 100) -> None:
        """Initialize memory monitor.

        Args:
            history_size: Maximum number of snapshots to keep
            snapshot_interval: Take snapshot every N requests
        """
        self.logger = logging.getLogger(__name__)
        self.process = psutil.Process()
        self.history: deque[MemorySnapshot] = deque(maxlen=history_size)
        self.request_stats: deque[RequestMemoryStats] = deque(maxlen=history_size)
        self.snapshot_interval = snapshot_interval
        self.request_count = 0
        self.start_time = datetime.now()

        # Take initial snapshot
        self._take_snapshot()

    def _take_snapshot(self) -> MemorySnapshot:
        """Take a memory snapshot.

        Returns:
            MemorySnapshot: Current memory usage snapshot
        """
        memory_info = self.process.memory_info()
        virtual_memory = psutil.virtual_memory()

        snapshot = MemorySnapshot(
            timestamp=datetime.now(),
            rss_mb=memory_info.rss / 1024 / 1024,
            vms_mb=memory_info.vms / 1024 / 1024,
            percent=self.process.memory_percent(),
            available_mb=virtual_memory.available / 1024 / 1024,
        )

        self.history.append(snapshot)
        return snapshot

    def get_current_memory(self) -> MemorySnapshot:
        """Get current memory usage.

        Returns:
            MemorySnapshot: Current memory snapshot
        """
        return self._take_snapshot()

    def record_request(
        self,
        path: str,
        method: str,
        duration_ms: float,
        memory_before_mb: float,
        memory_after_mb: float,
        status_code: int,
    ) -> None:
        """Record memory usage for a request.

        Args:
            path: Request path
            method: HTTP method
            duration_ms: Request duration in milliseconds
            memory_before_mb: Memory before request in MB
            memory_after_mb: Memory after request in MB
            status_code: HTTP status code
        """
        stats = RequestMemoryStats(
            path=path,
            method=method,
            timestamp=datetime.now(),
            duration_ms=duration_ms,
            memory_before_mb=memory_before_mb,
            memory_after_mb=memory_after_mb,
            memory_delta_mb=memory_after_mb - memory_before_mb,
            status_code=status_code,
        )

        self.request_stats.append(stats)

        # Log if memory delta is significant (>10MB)
        if abs(stats.memory_delta_mb) > 10:
            self.logger.warning(
                "Significant memory change: %s %s - Delta: %.2f MB "
                "(before: %.2f MB, after: %.2f MB)",
                method,
                path,
                stats.memory_delta_mb,
                memory_before_mb,
                memory_after_mb,
            )

    def get_statistics(self) -> dict[str, Any]:
        """Get memory statistics summary.

        Returns:
            dict[str, Any]: Memory statistics including current usage, history, and trends
        """
        if not self.history:
            return {"error": "No memory snapshots available"}

        current = self.history[-1]
        first = self.history[0]

        # Calculate trends
        memory_growth = current.rss_mb - first.rss_mb
        time_running = (datetime.now() - self.start_time).total_seconds()

        # Calculate average memory delta per request
        recent_requests = list(self.request_stats)[-100:]  # Last 100 requests
        avg_delta = (
            sum(r.memory_delta_mb for r in recent_requests) / len(recent_requests)
            if recent_requests
            else 0.0
        )

        # Find requests with highest memory impact
        top_memory_requests = sorted(
            self.request_stats, key=lambda x: abs(x.memory_delta_mb), reverse=True
        )[:10]

        return {
            "current_memory": {
                "rss_mb": round(current.rss_mb, 2),
                "vms_mb": round(current.vms_mb, 2),
                "percent": round(current.percent, 2),
                "available_mb": round(current.available_mb, 2),
            },
            "trends": {
                "memory_growth_mb": round(memory_growth, 2),
                "time_running_seconds": round(time_running, 2),
                "growth_rate_mb_per_hour": round(memory_growth / (time_running / 3600), 2)
                if time_running > 0
                else 0.0,
                "total_requests": self.request_count,
                "avg_memory_delta_per_request_mb": round(avg_delta, 4),
            },
            "history_stats": {
                "snapshots_count": len(self.history),
                "min_rss_mb": round(min(s.rss_mb for s in self.history), 2),
                "max_rss_mb": round(max(s.rss_mb for s in self.history), 2),
                "avg_rss_mb": round(sum(s.rss_mb for s in self.history) / len(self.history), 2),
            },
            "top_memory_requests": [
                {
                    "path": r.path,
                    "method": r.method,
                    "memory_delta_mb": round(r.memory_delta_mb, 2),
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in top_memory_requests
            ],
        }

    def force_garbage_collection(self) -> dict[str, Any]:
        """Force garbage collection and return statistics.

        This performs full garbage collection and also calls malloc_trim() to release
        freed memory back to the operating system, helping to reduce memory fragmentation.

        Returns:
            dict[str, Any]: Garbage collection statistics including malloc_trim results
        """
        before = self.get_current_memory()

        # Force full garbage collection and malloc_trim
        release_stats = force_memory_release()
        collected = release_stats["gc_collected"]
        malloc_trimmed = release_stats["malloc_trimmed"]

        after = self.get_current_memory()

        freed_mb = before.rss_mb - after.rss_mb

        self.logger.info(
            "Forced memory release: collected %d objects, malloc_trim=%d, freed %.2f MB",
            collected,
            malloc_trimmed,
            freed_mb,
        )

        return {
            "objects_collected": collected,
            "malloc_trimmed": malloc_trimmed,
            "memory_before_mb": round(before.rss_mb, 2),
            "memory_after_mb": round(after.rss_mb, 2),
            "memory_freed_mb": round(freed_mb, 2),
        }
