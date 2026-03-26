"""Tests for scan limiter module."""

import asyncio

import pytest

from foxhole_stockpiles.api.scan_limiter import ScanLimiter


class TestScanLimiter:
    """Test cases for ScanLimiter."""

    def test_disabled_when_zero(self) -> None:
        """Test that limiter is disabled when max_concurrent is 0."""
        limiter = ScanLimiter(max_concurrent=0)
        assert not limiter.is_enabled
        assert limiter.max_concurrent == 0

    def test_enabled_when_positive(self) -> None:
        """Test that limiter is enabled when max_concurrent is positive."""
        limiter = ScanLimiter(max_concurrent=2)
        assert limiter.is_enabled
        assert limiter.max_concurrent == 2

    @pytest.mark.asyncio
    async def test_acquire_disabled(self) -> None:
        """Test acquire works when disabled."""
        limiter = ScanLimiter(max_concurrent=0)
        async with limiter.acquire():
            pass
        stats = limiter.get_stats()
        assert stats["total_scans"] == 1
        assert stats["queued_scans"] == 0

    @pytest.mark.asyncio
    async def test_acquire_enabled(self) -> None:
        """Test acquire works when enabled."""
        limiter = ScanLimiter(max_concurrent=2)
        async with limiter.acquire():
            stats = limiter.get_stats()
            assert stats["current_active"] == 1
        stats = limiter.get_stats()
        assert stats["current_active"] == 0
        assert stats["total_scans"] == 1

    @pytest.mark.asyncio
    async def test_concurrent_limit(self) -> None:
        """Test that concurrent operations are limited."""
        limiter = ScanLimiter(max_concurrent=2)
        active_count = 0
        max_active = 0

        async def work() -> None:
            nonlocal active_count, max_active
            async with limiter.acquire():
                active_count += 1
                max_active = max(max_active, active_count)
                await asyncio.sleep(0.1)
                active_count -= 1

        # Run 5 concurrent tasks with limit of 2
        await asyncio.gather(*[work() for _ in range(5)])

        assert max_active == 2
        stats = limiter.get_stats()
        assert stats["total_scans"] == 5
        assert stats["queued_scans"] == 3  # 3 had to wait

    def test_get_stats(self) -> None:
        """Test get_stats returns expected fields."""
        limiter = ScanLimiter(max_concurrent=2)
        stats = limiter.get_stats()
        assert "max_concurrent" in stats
        assert "enabled" in stats
        assert "total_scans" in stats
        assert "queued_scans" in stats
        assert "avg_queue_wait_ms" in stats
        assert "max_queue_wait_ms" in stats
        assert "current_active" in stats
        assert "current_waiting" in stats
