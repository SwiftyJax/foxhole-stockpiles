"""Template manager for handling multiple resolution databases and icon matching."""

import asyncio
import logging
import pickle
import time
from pathlib import Path
from threading import Lock
from typing import ClassVar, cast

import cv2
import numpy as np
from numpy.typing import NDArray

from foxhole_stockpiles.core.utils import compute_icon_phash, hamming_distance
from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.models.icon_template import IconTemplate
from foxhole_stockpiles.models.match_result import MatchResult
from foxhole_stockpiles.services.template_database import TemplateDatabase

logger = logging.getLogger(__name__)


class TemplateManager:
    """Manages multiple resolution-specific template databases."""

    # Class-level shared cache (shared across all instances)
    _shared_databases: ClassVar[dict[tuple[Path, SupportedResolution], TemplateDatabase]] = {}
    _shared_lock: ClassVar[Lock] = Lock()

    def __init__(self, database_path: Path) -> None:
        """Initialize template manager.

        Args:
            database_path (Path): Path to the binary database file
        """
        self.database_path = database_path
        self.active_database: TemplateDatabase | None = None
        self.current_resolution: SupportedResolution | None = None

    async def load_database(self, resolution: SupportedResolution) -> TemplateDatabase:
        """Load or get cached database for specific resolution.

        Args:
            resolution (SupportedResolution): Target resolution

        Returns:
            TemplateDatabase: Loaded template database
        """
        # Use shared cache key
        cache_key = (self.database_path, resolution)

        # Check shared cache (thread-safe)
        with self._shared_lock:
            if cache_key in self._shared_databases:
                return self._shared_databases[cache_key]

        # Load from file if not in cache
        logger.debug(
            "Loading template database for resolution %s from %s",
            resolution,
            self.database_path,
        )

        # Load from binary file
        def load_pickle() -> dict[SupportedResolution, TemplateDatabase]:
            """Load pickle file synchronously."""
            with open(self.database_path, "rb") as f:
                data = pickle.load(f)
                return cast(dict[SupportedResolution, TemplateDatabase], data)

        all_databases = await asyncio.to_thread(load_pickle)

        if resolution not in all_databases:
            raise ValueError(f"Resolution {resolution} not found in database")

        database = all_databases[resolution]

        # Cache in shared cache
        with self._shared_lock:
            self._shared_databases[cache_key] = database

        logger.debug(
            "Loaded database with %d templates for resolution %s",
            len(database.templates),
            resolution,
        )

        return database

    async def get_supported_mods(self) -> set[str]:
        """Get all mods supported in the database.

        Uses 1080p resolution as the reference since all resolutions
        should have the same set of mods.

        Returns:
            set[str]: Set of supported mod names
        """
        database = await self.load_database(SupportedResolution.R_1080)
        return database.get_available_mods()

    async def set_active_resolution(self, screenshot_height: int) -> SupportedResolution:
        """Set active resolution based on screenshot dimensions.

        Args:
            screenshot_height (int): Height of the screenshot in pixels

        Returns:
            SupportedResolution: Selected resolution for processing
        """
        # Find exact or closest resolution
        target_resolution = self._find_best_resolution(height=screenshot_height)

        if self.current_resolution != target_resolution:
            logger.debug(
                "Switching to resolution %s for screenshot height %d",
                target_resolution,
                screenshot_height,
            )
            self.active_database = await self.load_database(resolution=target_resolution)
            self.current_resolution = target_resolution

        return target_resolution

    def _find_best_resolution(self, height: int) -> SupportedResolution:
        """Find the best matching resolution for given height.

        Args:
            height (int): Screenshot height in pixels

        Returns:
            SupportedResolution: Best matching resolution
        """
        resolutions = [int(r.value) for r in SupportedResolution]

        # Find exact match first
        if str(height) in [r.value for r in SupportedResolution]:
            return SupportedResolution(str(height))

        # Find closest resolution
        closest = min(resolutions, key=lambda x: abs(x - height))
        return SupportedResolution(str(closest))

    def match_icon(
        self,
        icon_image: NDArray[np.uint8] | None = None,
        faction: ItemFaction | None = None,
        mod: str | None = None,
        category: ItemCategory | None = None,
        crated: bool | None = None,
        code: str | None = None,
        excluded_codes: list[str] | None = None,
        phash_threshold: int = 12,
        max_ncc_candidates: int = 25,
        early_exit_threshold: float = 0.0,
        top_n: int = 5,
    ) -> MatchResult:
        """Get candidates and optionally perform icon matching.

        Args:
            icon_image (NDArray[np.uint8] | None): Optional icon image to match
            faction (ItemFaction | None): Optional faction filter
            mod (str | None): Optional mod filter
            category (ItemCategory | None): Optional category filter
            crated (bool | None): Optional crated filter
            code (str | None): Optional item code filter
            excluded_codes (list[str] | None): Optional list of item codes to exclude from matching
            phash_threshold (int): Maximum Hamming distance for pHash filtering
            max_ncc_candidates (int): Maximum candidates for NCC optimization
            early_exit_threshold (float): Confidence threshold for immediate exit (0.0 = disabled)
            top_n (int): Number of top matches to return with confidence scores (default: 5)

        Returns:
            MatchResult: Candidates list and optional icon match result
        """
        if not self.active_database:
            raise ValueError("No active database loaded")

        # Get candidates using filters
        candidates = self.active_database.get_candidates(
            faction=faction,
            mod=mod,
            category=category,
            crated=crated,
            code=code,
            excluded_codes=excluded_codes,
        )

        icon_result = None
        confidence_result: float = 0.0

        if icon_image is None:
            return MatchResult(
                candidates=candidates, icon=None, confidence=0.0, tested_candidates=0
            )

        start_time = time.perf_counter()

        # pHash pre-filtering
        final_candidates = candidates
        phash_time_ms = 0.0

        if len(candidates) > max_ncc_candidates:
            phash_start = time.perf_counter()
            icon_phash = compute_icon_phash(icon_image)

            phash_filtered = []
            item_codes_included = set()

            for candidate_idx in candidates:
                template = self.active_database.templates[candidate_idx]
                distance = hamming_distance(icon_phash, template.phash)
                if distance <= phash_threshold:
                    phash_filtered.append((candidate_idx, distance))
                    item_codes_included.add(template.code)

            # Sort by pHash similarity and take top candidates
            phash_filtered.sort(key=lambda x: x[1])
            final_candidates = [idx for idx, _ in phash_filtered[:max_ncc_candidates]]

            phash_time_ms = (time.perf_counter() - phash_start) * 1000

        # Template matching
        ncc_start = time.perf_counter()
        best_match = None
        best_confidence = 0.0
        candidates_tested = 0
        all_matches: list[tuple[float, IconTemplate]] = []

        for candidate_idx in final_candidates:
            candidates_tested += 1
            template = self.active_database.templates[candidate_idx]

            result = cv2.matchTemplate(
                image=icon_image, templ=cast(cv2.Mat, template.image), method=cv2.TM_CCOEFF_NORMED
            )
            _, confidence, _, _ = cv2.minMaxLoc(result)

            # Store all matches for top N
            all_matches.append((confidence, template))

            if confidence > best_confidence:
                best_confidence = confidence
                best_match = template

            # Early exit if very high confidence found (only if early_exit_threshold > 0)
            if early_exit_threshold > 0.0 and confidence >= early_exit_threshold:
                logger.debug(
                    "Early exit: found %.3f confidence (>= %.3f) after testing %d candidates",
                    confidence,
                    early_exit_threshold,
                    candidates_tested,
                )
                break

        # Sort all matches by confidence and get top N
        all_matches.sort(key=lambda x: x[0], reverse=True)
        top_matches = [(template, conf) for conf, template in all_matches[:top_n]]

        ncc_time_ms = (time.perf_counter() - ncc_start) * 1000
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000

        logger.debug(
            "Icon matching took %.2f ms total (pHash: %.2f, NCC: %.2f) tested %d of %d candidates.",
            total_time_ms,
            phash_time_ms,
            ncc_time_ms,
            candidates_tested,
            len(final_candidates),
        )

        # Always return the best match regardless of confidence
        if best_match:
            icon_result = best_match
            confidence_result = best_confidence

        return MatchResult(
            candidates=candidates,
            icon=icon_result,
            confidence=confidence_result,
            best_match=best_match,
            best_confidence=best_confidence,
            tested_candidates=candidates_tested,
            top_matches=top_matches,
        )

    def __repr__(self) -> str:
        """String representation of the template manager."""
        return (
            f"TemplateManager(database_path={self.database_path}, "
            f"loaded_resolutions={len(self._shared_databases)}, "
            f"current_resolution={self.current_resolution})"
        )
