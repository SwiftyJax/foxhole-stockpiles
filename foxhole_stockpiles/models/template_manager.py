"""Template manager for handling multiple resolution databases and icon matching."""

import logging
import pickle
import time
from pathlib import Path
from typing import cast

import cv2
import numpy as np
from numpy.typing import NDArray

from foxhole_stockpiles.core.utils import compute_icon_phash, hamming_distance
from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.models.database_statistics import TemplateManagerStatistics
from foxhole_stockpiles.models.match_result import MatchResult
from foxhole_stockpiles.models.template_database import TemplateDatabase

logger = logging.getLogger(__name__)


class TemplateManager:
    """Manages multiple resolution-specific template databases."""

    def __init__(self, database_path: Path) -> None:
        """Initialize template manager.

        Args:
            database_path (Path): Path to the binary database file
        """
        self.database_path = database_path
        self.databases: dict[SupportedResolution, TemplateDatabase] = {}
        self.active_database: TemplateDatabase | None = None
        self.current_resolution: SupportedResolution | None = None

    def load_database(self, resolution: SupportedResolution) -> TemplateDatabase:
        """Load or get cached database for specific resolution.

        Args:
            resolution (SupportedResolution): Target resolution

        Returns:
            TemplateDatabase: Loaded template database
        """
        if resolution not in self.databases:
            logger.info("Loading template database for resolution %s", resolution)

            # Load from binary file
            with open(self.database_path, "rb") as f:
                all_databases = pickle.load(f)

            if resolution not in all_databases:
                raise ValueError(f"Resolution {resolution} not found in database")

            self.databases[resolution] = all_databases[resolution]

        return self.databases[resolution]

    def set_active_resolution(self, screenshot_height: int) -> SupportedResolution:
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
            self.active_database = self.load_database(resolution=target_resolution)
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
        confidence_threshold: float = 0.8,
        phash_threshold: int = 12,
        max_ncc_candidates: int = 10,
    ) -> MatchResult:
        """Get candidates and optionally perform icon matching.

        Args:
            icon_image (NDArray[np.uint8] | None): Optional icon image to match
            faction (ItemFaction | None): Optional faction filter
            mod (str | None): Optional mod filter
            category (ItemCategory | None): Optional category filter
            crated (bool | None): Optional crated filter
            code (str | None): Optional item code filter
            confidence_threshold (float): Minimum confidence for icon match
            phash_threshold (int): Maximum Hamming distance for pHash filtering
            max_ncc_candidates (int): Maximum candidates for NCC optimization

        Returns:
            MatchResult: Candidates list and optional icon match result
        """
        if not self.active_database:
            raise ValueError("No active database loaded")

        # Get candidates using filters
        candidates = self.active_database.get_candidates(
            faction=faction, mod=mod, category=category, crated=crated, code=code
        )

        icon_result = None
        confidence_result = None

        # Perform icon matching if image is provided
        if icon_image is None:
            return MatchResult(
                candidates=candidates, icon=icon_result, confidence=confidence_result
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
                if template.phash is not None:
                    distance = hamming_distance(icon_phash, template.phash)
                    if distance <= phash_threshold:
                        phash_filtered.append((candidate_idx, distance))
                        item_codes_included.add(template.code)
                else:
                    # Include templates without pHash in fallback
                    phash_filtered.append((candidate_idx, phash_threshold + 1))

            # Sort by pHash similarity and take top candidates
            phash_filtered.sort(key=lambda x: x[1])
            final_candidates = [idx for idx, _ in phash_filtered[:max_ncc_candidates]]

            phash_time_ms = (time.perf_counter() - phash_start) * 1000

        # Template matching
        ncc_start = time.perf_counter()
        best_match = None
        best_confidence = 0.0

        for candidate_idx in final_candidates:
            template = self.active_database.templates[candidate_idx]

            result = cv2.matchTemplate(
                image=icon_image, templ=cast(cv2.Mat, template.image), method=cv2.TM_CCOEFF_NORMED
            )
            _, confidence, _, _ = cv2.minMaxLoc(result)

            if confidence > best_confidence:
                best_confidence = confidence
                best_match = template

        ncc_time_ms = (time.perf_counter() - ncc_start) * 1000
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000

        logger.debug(
            "Icon matching took %.2f ms total (pHash: %.2f ms, NCC: %.2f ms) for %d→%d candidates.",
            total_time_ms,
            phash_time_ms,
            ncc_time_ms,
            len(candidates),
            len(final_candidates),
        )

        if best_match and best_confidence >= confidence_threshold:
            icon_result = best_match
            confidence_result = best_confidence

        return MatchResult(candidates=candidates, icon=icon_result, confidence=confidence_result)

    def get_statistics(self) -> TemplateManagerStatistics:
        """Get template manager and database statistics.

        Returns:
            TemplateManagerStatistics: Complete statistics as Pydantic model
        """
        loaded_resolutions = len(self.databases)
        current_resolution = self.current_resolution.value if self.current_resolution else None
        active_templates = len(self.active_database.templates) if self.active_database else 0

        # Get database statistics if active database exists
        database_stats = None
        if self.active_database:
            database_stats = self.active_database.get_statistics()

        return TemplateManagerStatistics.from_manager_and_database(
            loaded_resolutions=loaded_resolutions,
            current_resolution=current_resolution,
            active_templates=active_templates,
            database_stats=database_stats,
        )

    def __repr__(self) -> str:
        """String representation of the template manager."""
        return (
            f"TemplateManager(database_path={self.database_path}, "
            f"loaded_resolutions={len(self.databases)}, "
            f"current_resolution={self.current_resolution})"
        )
