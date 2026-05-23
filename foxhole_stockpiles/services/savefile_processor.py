"""Service to process Foxhole save files for stockpile data."""

import asyncio
import logging
from collections import defaultdict
from pathlib import Path

from foxhole_stockpiles.models.stockpile import Stockpile
from foxhole_stockpiles.services.output_coordinator import OutputCoordinator
from foxhole_stockpiles.services.sav_parser import parse_save

logger = logging.getLogger(__name__)


class SaveFileProcessor:
    """Processes save files and optionally watches for changes."""

    def __init__(
        self,
        file_path: Path,
        output_coordinator: OutputCoordinator,
        poll_interval: float = 1.0,
        emit_all_on_start: bool = False,
    ) -> None:
        """Initialize the processor.

        Args:
            file_path (Path): Path to the save file to monitor.
            output_coordinator (OutputCoordinator): Output coordinator for handlers.
            poll_interval (float): Polling interval in seconds.
            emit_all_on_start (bool): Emit all stockpiles on first run.
        """
        self._file_path = file_path
        self._output_coordinator = output_coordinator
        self._poll_interval = poll_interval
        self._emit_all_on_start = emit_all_on_start
        self._last_mtime: float | None = None
        self._running = False

        # Track stockpiles by key -> timestamp string for change detection
        self._stockpile_cache: dict[str, str] = {}

    @property
    def file_path(self) -> Path:
        """Get the monitored file path."""
        return self._file_path

    @property
    def poll_interval(self) -> float:
        """Get the polling interval."""
        return self._poll_interval

    @poll_interval.setter
    def poll_interval(self, value: float) -> None:
        """Set the polling interval."""
        self._poll_interval = value

    @property
    def is_running(self) -> bool:
        """Check if processor is running in watch mode."""
        return self._running

    def _group_by_location(self, stockpiles: list[Stockpile]) -> dict[str, list[Stockpile]]:
        """Group stockpiles by their location (coords).

        Args:
            stockpiles (list[Stockpile]): List of stockpiles to group.

        Returns:
            dict[str, list[Stockpile]]: Stockpiles grouped by location key.
        """
        groups: dict[str, list[Stockpile]] = defaultdict(list)
        for stockpile in stockpiles:
            # Use coords as location key (hex:coords)
            coords_key = stockpile.coords.to_key() if stockpile.coords else "0,0"
            location_key = f"{stockpile.hex}:{coords_key}"
            groups[location_key].append(stockpile)
        return dict(groups)

    async def _output_results(self, stockpiles: list[Stockpile]) -> None:
        """Output stockpiles through the handler pipeline, one call per location.

        Stockpiles are grouped by their coordinates. Each location (public + reserves)
        triggers a separate handler call.

        Args:
            stockpiles (list[Stockpile]): List of stockpiles to output.
        """
        if not stockpiles:
            return

        # Group by location and output each group separately
        location_groups = self._group_by_location(stockpiles)
        for location_stockpiles in location_groups.values():
            await self._output_coordinator.handle_output(location_stockpiles)

    def _detect_changes(
        self, stockpiles: list[Stockpile]
    ) -> tuple[list[Stockpile], list[Stockpile], list[str]]:
        """Detect which stockpiles have changed.

        Uses timestamp string comparison for change detection since fs-sav
        doesn't expose raw UE ticks.

        Args:
            stockpiles (list[Stockpile]): Current stockpiles.

        Returns:
            tuple: (updated_stockpiles, new_stockpiles, removed_keys)
        """
        updated: list[Stockpile] = []
        new: list[Stockpile] = []
        current_keys: set[str] = set()

        for stockpile in stockpiles:
            key = stockpile.to_key()
            current_keys.add(key)
            timestamp_str = stockpile.timestamp.isoformat()
            cached_timestamp = self._stockpile_cache.get(key)

            if cached_timestamp is None:
                # New stockpile
                new.append(stockpile)
                self._stockpile_cache[key] = timestamp_str
            elif cached_timestamp != timestamp_str:
                # Timestamp changed
                updated.append(stockpile)
                self._stockpile_cache[key] = timestamp_str
            # else: unchanged, skip

        # Find removed stockpiles
        removed_keys = [k for k in self._stockpile_cache if k not in current_keys]
        for key in removed_keys:
            del self._stockpile_cache[key]

        return updated, new, removed_keys

    async def _process_file(self, is_initial: bool = False) -> list[Stockpile]:
        """Process the save file and output changed stockpiles.

        Args:
            is_initial (bool): Whether this is the initial load.

        Returns:
            list[Stockpile]: List of changed stockpiles that were output.
        """
        logger.info("Processing file...")

        try:
            stockpiles = await asyncio.to_thread(parse_save, self._file_path)

            if not stockpiles:
                logger.info("No stockpiles found in save file.")
                return []

            # On initial load with emit_all_on_start, output everything
            if is_initial and self._emit_all_on_start:
                # Initialize cache
                for stockpile in stockpiles:
                    self._stockpile_cache[stockpile.to_key()] = stockpile.timestamp.isoformat()

                logger.info("Initial load: %d stockpile(s)", len(stockpiles))
                await self._output_results(stockpiles)
                return stockpiles

            # Detect changes
            updated, new, removed = self._detect_changes(stockpiles)

            total_changes = len(updated) + len(new) + len(removed)
            if total_changes == 0:
                logger.debug("No changes detected.")
                return []

            # Log changes
            if new:
                logger.info("New: %d stockpile(s)", len(new))
            if updated:
                logger.info("Updated: %d stockpile(s)", len(updated))
            if removed:
                logger.info("Removed: %d stockpile(s)", len(removed))

            # Output changed stockpiles (new + updated)
            changed_stockpiles = new + updated
            if changed_stockpiles:
                await self._output_results(changed_stockpiles)

            return changed_stockpiles

        except Exception as e:
            logger.error("Error processing file: %s", e)
            return []

    async def run_once(self) -> list[Stockpile]:
        """Process the file once without monitoring.

        Returns:
            list[Stockpile]: List of stockpiles found.
        """
        return await self._process_file(is_initial=True)

    async def run(self) -> None:
        """Run the file processor in watch mode."""
        self._running = True
        logger.info("Watching: %s", self._file_path)
        logger.info("Poll interval: %ss", self._poll_interval)

        try:
            # Process once immediately (initial load)
            if self._file_path.exists():
                self._last_mtime = self._file_path.stat().st_mtime
                await self._process_file(is_initial=True)

            while self._running:
                try:
                    await asyncio.sleep(self._poll_interval)

                    if not self._file_path.exists():
                        continue

                    current_mtime = self._file_path.stat().st_mtime

                    # Only process if file was modified
                    if self._last_mtime is None or current_mtime > self._last_mtime:
                        self._last_mtime = current_mtime
                        await self._process_file(is_initial=False)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Processor error: %s", e)
        finally:
            self._running = False

    def stop(self) -> None:
        """Stop the monitor."""
        self._running = False

    def clear_cache(self) -> None:
        """Clear the stockpile cache."""
        self._stockpile_cache.clear()
        self._last_mtime = None
