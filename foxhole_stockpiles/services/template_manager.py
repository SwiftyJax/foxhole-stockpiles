"""Template manager for handling multiple resolution databases and icon matching."""

import asyncio
import logging
import pickle
import time
from pathlib import Path
from threading import Lock
from typing import ClassVar, cast

import cv2
import h5py
import numpy as np
from numpy.typing import NDArray

from foxhole_stockpiles.core.utils import compute_icon_phash, hamming_distance
from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.models.icon_template import IconTemplate
from foxhole_stockpiles.models.match_result import MatchResult
from foxhole_stockpiles.services.template_database import DATABASE_VERSION, TemplateDatabase

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

    def _check_database_version(self, file_path: Path) -> int:
        """Check database format and return version number.

        Args:
            file_path (Path): Path to database file

        Returns:
            int: Version number (0=invalid/unknown, 1=pickle, 2+=HDF5 with version)
        """
        try:
            # Try to open as HDF5
            with h5py.File(str(file_path), "r") as f:
                # If it's a valid HDF5 file, check for version attribute
                if "version" in f.attrs:
                    return int(f.attrs["version"])  # type: ignore[arg-type]
                # Valid HDF5 but no version attribute (shouldn't happen, but treat as v2)
                return 2
        except (OSError, Exception):
            # Not HDF5, check if it's pickle
            try:
                with open(file_path, "rb") as f:
                    pickle.load(f)
                return 1  # Pickle format is version 1
            except Exception:
                return 0  # Invalid or unknown format

    async def load_database(self, resolution: SupportedResolution) -> TemplateDatabase:
        """Load or get cached database for specific resolution.

        Supports HDF5 format (version 2). Old pickle formats (version 1) must be migrated
        using 'fs update-db' command.

        Args:
            resolution (SupportedResolution): Target resolution

        Returns:
            TemplateDatabase: Loaded template database

        Raises:
            FileNotFoundError: If database file not found
            ValueError: If database format is invalid or needs migration
        """
        # Use shared cache key
        cache_key = (self.database_path, resolution)

        # Check shared cache (thread-safe)
        with self._shared_lock:
            if cache_key in self._shared_databases:
                return self._shared_databases[cache_key]

        # Check if database exists
        if not self.database_path.exists():
            raise FileNotFoundError(
                f"Template database not found: {self.database_path}\n\n"
                f"Please build a database first:\n"
                f"  fs database-builder --catalog catalog.json --templates templates/ "
                f"--database {self.database_path}"
            )

        # Check database format and version
        db_version = self._check_database_version(self.database_path)

        if db_version == 0:
            raise ValueError(
                f"Database file format is not recognized: {self.database_path}\n"
                f"File may be corrupted or in an unsupported format."
            )

        if db_version != DATABASE_VERSION:
            raise ValueError(
                f"Database version {db_version} does not match expected version {DATABASE_VERSION}."
                f"Please migrate your database using: "
                f"fs update-db --database-path {self.database_path}"
            )

        # Load from HDF5 file
        logger.debug(
            "Loading template database for resolution %s from %s",
            resolution,
            self.database_path,
        )

        def load_hdf5() -> TemplateDatabase:
            """Load HDF5 file synchronously."""
            with h5py.File(str(self.database_path), "r") as f:
                # Check if resolution exists
                if resolution.value not in f:
                    available = list(f.keys())
                    raise ValueError(
                        f"Resolution {resolution.value} not found in database.\n"
                        f"Available resolutions: {', '.join(available)}"
                    )

                # Load the specific resolution group
                group = f[resolution.value]
                database = TemplateDatabase.load_from_hdf5_group(
                    group=cast(h5py.Group, group), resolution=resolution
                )

            return database

        database = await asyncio.to_thread(load_hdf5)

        # Cache in shared cache
        with self._shared_lock:
            self._shared_databases[cache_key] = database

        logger.debug(
            "Loaded database with %d templates for resolution %s",
            len(database.templates),
            resolution,
        )

        return database

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
        confidence_gap: float = 0.0,
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
            confidence_gap (float): Gap for returning alternative candidates (0.0 = disabled)
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

        # Calculate gap candidates if confidence_gap > 0
        gap_candidates: list[tuple[IconTemplate, float]] = []
        if confidence_gap > 0.0 and best_match and best_confidence > 0.0:
            min_confidence = best_confidence - confidence_gap

            for conf, template in all_matches:
                # Skip if it's the best match itself
                if template.code == best_match.code and template.crated == best_match.crated:
                    continue

                # Only include candidates within the gap that match category, crated, and mod
                if (
                    conf >= min_confidence
                    and conf < best_confidence
                    and template.category == best_match.category
                    and template.crated == best_match.crated
                    and template.mod == best_match.mod
                ):
                    gap_candidates.append((template, conf))

            # Sort gap candidates by confidence (highest first)
            gap_candidates.sort(key=lambda x: x[1], reverse=True)

            if gap_candidates:
                logger.debug(
                    "Found %d gap candidates within %.3f of best match (%.3f)",
                    len(gap_candidates),
                    confidence_gap,
                    best_confidence,
                )

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
            gap_candidates=gap_candidates,
        )

    @staticmethod
    def save_databases_to_hdf5(
        databases: dict[SupportedResolution, TemplateDatabase], output_path: Path
    ) -> None:
        """Save multiple resolution databases to a single HDF5 file.

        Args:
            databases (dict[SupportedResolution, TemplateDatabase]): Databases to save
            output_path (Path): Output file path

        Raises:
            ValueError: If databases dict is empty
        """
        if not databases:
            raise ValueError("Cannot save empty databases dictionary")

        logger.debug("Saving %d resolution(s) to HDF5 file: %s", len(databases), output_path)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with h5py.File(str(output_path), "w") as f:
            # Store database-level metadata
            f.attrs["version"] = DATABASE_VERSION
            f.attrs["format"] = "hdf5"
            f.attrs["resolutions"] = [r.value for r in databases.keys()]

            # Save each resolution as a group
            for resolution, database in databases.items():
                group = f.create_group(resolution.value)
                database.save_to_hdf5_group(group)

        logger.debug(
            "Saved %d resolution(s) to %s (%.1f MB)",
            len(databases),
            output_path,
            output_path.stat().st_size / (1024 * 1024),
        )

    def needs_migration(self) -> bool:
        """Check if database needs to be migrated to current version.

        Returns:
            bool: True if database exists and is not at the current version
        """
        if not self.database_path.exists():
            return False

        db_version = self._check_database_version(self.database_path)
        # Version 0 means invalid/corrupted, not a migration case
        return db_version != 0 and db_version != DATABASE_VERSION

    def migrate_database(self, output_path: Path | None = None) -> None:
        """Migrate database from current version to latest version.

        Applies all necessary migrations sequentially (e.g., v1→v2→v3→v4).

        Args:
            output_path (Path | None): Output path for migrated database. If None, uses
                database_path with appropriate extension

        Raises:
            FileNotFoundError: If database_path doesn't exist
            ValueError: If database is corrupted or migration fails
        """
        if not self.database_path.exists():
            raise FileNotFoundError(f"Database file not found: {self.database_path}")

        # Get current version
        current_version = self._check_database_version(self.database_path)

        if current_version == 0:
            raise ValueError("Database file is corrupted or in an unrecognized format")

        if current_version == DATABASE_VERSION:
            raise ValueError(f"Database is already at version {DATABASE_VERSION}")

        logger.info(
            "Starting migration from version %d to version %d", current_version, DATABASE_VERSION
        )

        while current_version < DATABASE_VERSION:
            next_version = current_version + 1
            logger.info("Applying migration: v%d → v%d", current_version, next_version)

            match current_version:
                case 1:
                    self._migrate_v1_to_v2(input_path=self.database_path, output_path=output_path)
                case _:
                    logger.warning(
                        f"No migration path from version {current_version} to {next_version}"
                    )

            current_version = next_version

        logger.info("Migration complete: now at version %d", DATABASE_VERSION)

    def _migrate_v1_to_v2(self, input_path: Path, output_path: Path | None = None) -> None:
        """Migrate v1 (pickle) database to v2 (HDF5) format.

        Args:
            input_path (Path): Input pickle database path
            output_path (Path | None): Output path for HDF5 file. If None, uses
                input_path with .h5 extension

        Raises:
            FileNotFoundError: If input_path doesn't exist
            ValueError: If file is not a valid pickle database
        """
        import time

        if not input_path.exists():
            raise FileNotFoundError(f"Database file not found: {input_path}")

        # Determine output path
        _output_path = output_path or input_path.with_suffix(".h5")

        # Load pickle file
        load_start = time.perf_counter()
        with open(input_path, "rb") as f:
            try:
                all_databases = pickle.load(f)
            except Exception as e:
                raise ValueError(f"Failed to load pickle database: {e}") from e
        load_time = time.perf_counter() - load_start
        logger.info("Pickle load time: %.2f seconds", load_time)

        if not isinstance(all_databases, dict):
            raise ValueError(f"Expected dict of databases, got {type(all_databases).__name__}")

        # Get pickle file size before conversion
        pickle_size_mb = input_path.stat().st_size / (1024 * 1024)

        # Convert to HDF5 using centralized method
        logger.debug("Converting %d resolution(s)...", len(all_databases))
        convert_start = time.perf_counter()
        self.save_databases_to_hdf5(databases=all_databases, output_path=_output_path)
        convert_time = time.perf_counter() - convert_start
        logger.info("HDF5 conversion time: %.2f seconds", convert_time)

        # Get HDF5 file size after conversion
        hdf5_size_mb = _output_path.stat().st_size / (1024 * 1024)

        logger.info(
            "Migration complete: %d resolutions, %.1f MB -> %.1f MB (%.1f%% of original)",
            len(all_databases),
            pickle_size_mb,
            hdf5_size_mb,
            (hdf5_size_mb / pickle_size_mb * 100) if pickle_size_mb > 0 else 0,
        )
        logger.info(
            "Total time: %.2f seconds (load: %.2f, convert: %.2f)",
            load_time + convert_time,
            load_time,
            convert_time,
        )

    def __repr__(self) -> str:
        """String representation of the template manager."""
        return (
            f"TemplateManager(database_path={self.database_path}, "
            f"loaded_resolutions={len(self._shared_databases)}, "
            f"current_resolution={self.current_resolution})"
        )
