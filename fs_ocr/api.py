"""Public API for fs_ocr package.

This module defines the public contract for the OCR scanner.
All public types are re-exported from __init__.py.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import cv2
import numpy as np
from pydantic import BaseModel, Field

from foxhole_stockpiles import __version__
from foxhole_stockpiles.core.settings.sections.scanner import ScannerSettings
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_language import SupportedLanguage
from foxhole_stockpiles.models.stockpile import Stockpile
from fs_ocr._impl.coordinator import OCRCoordinator
from fs_ocr._impl.template_database import DATABASE_VERSION

if TYPE_CHECKING:
    from numpy.typing import NDArray

SCHEMA_VERSION = "1"

logger = logging.getLogger(__name__)


class ScannerConfig(BaseModel):
    """Configuration for the OCR scanner."""

    database_path: Path = Field(description="Path to the HDF5 template database")
    tessdata_path: str = Field(default="tessdata", description="Path to Tesseract data directory")
    custom_model: str = Field(
        default="renner_numbers", description="Name of custom Tesseract model"
    )
    template_cache_size: int = Field(
        default=16, ge=0, description="Number of resolution databases to cache"
    )
    early_exit_threshold: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Early exit threshold for icon matching"
    )
    confidence_gap: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Gap within which to include alternative candidates",
    )
    extract_icons: bool = Field(
        default=False, description="Whether to extract icons to disk for debugging"
    )


class ScannerInfo(BaseModel):
    """Metadata about the OCR scanner."""

    schema_version: Literal["1"] = "1"
    implementation: Literal["python", "rust"] = "python"
    version: str
    database_version: str | None = None


class OCRScanner:
    """Stateful OCR scanner. Construct once, scan many images."""

    def __init__(self, config: ScannerConfig) -> None:
        """Initialize the OCR scanner.

        Args:
            config (ScannerConfig): Scanner configuration.

        Raises:
            FileNotFoundError: If database_path does not exist.
            ValueError: If configuration is invalid.
        """
        if not config.database_path.exists():
            raise FileNotFoundError(f"Database not found: {config.database_path}")

        # Convert to ScannerSettings for the coordinator
        scanner_settings = ScannerSettings(
            database_path=config.database_path,
            template_cache_size=config.template_cache_size,
            early_exit_threshold=config.early_exit_threshold,
            confidence_gap=config.confidence_gap,
            extract_icons=config.extract_icons,
        )

        self._config = config
        self._coordinator = OCRCoordinator(scanner_settings, event_bus=None)
        self._closed = False

    async def scan(
        self,
        image: bytes | Path | NDArray[np.uint8],
        languages: list[SupportedLanguage] | None = None,
        faction: ItemFaction | None = None,
    ) -> Stockpile:
        """Scan an image and extract stockpile data.

        Args:
            image: Image data as bytes, file path, or numpy array (BGR format).
            languages: Languages for text detection. Defaults to all supported.
            faction: Faction filter for icon matching. Defaults to None (no filter).

        Returns:
            Stockpile: Detected stockpile with items and metadata.

        Raises:
            ValueError: If image is invalid or analysis fails.
            RuntimeError: If scanner has been closed.
        """
        if self._closed:
            raise RuntimeError("Scanner has been closed")

        # Convert image to numpy array
        img_array: NDArray[np.uint8]
        if isinstance(image, bytes):
            nparr = np.frombuffer(image, np.uint8)
            decoded = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if decoded is None:
                raise ValueError("Failed to decode image bytes")
            img_array = np.asarray(decoded, dtype=np.uint8)
        elif isinstance(image, Path):
            loaded = cv2.imread(str(image))
            if loaded is None:
                raise ValueError(f"Failed to read image: {image}")
            img_array = np.asarray(loaded, dtype=np.uint8)
        else:
            img_array = image

        return await self._coordinator.analyze_stockpile(
            image=img_array,
            languages=languages,
            faction=faction,
        )

    def scan_sync(
        self,
        image: bytes | Path | NDArray[np.uint8],
        languages: list[SupportedLanguage] | None = None,
        faction: ItemFaction | None = None,
    ) -> Stockpile:
        """Synchronous version of scan.

        This is a convenience wrapper for simple scripts. It cannot be called
        from within a running event loop; use the async ``scan`` method instead.

        Args:
            image: Image data as bytes, file path, or numpy array (BGR format).
            languages: Languages for text detection. Defaults to all supported.
            faction: Faction filter for icon matching. Defaults to None (no filter).

        Returns:
            Stockpile: Detected stockpile with items and metadata.

        Raises:
            RuntimeError: If called from within a running event loop.
        """
        return asyncio.run(self.scan(image, languages, faction))

    def info(self) -> ScannerInfo:
        """Get scanner metadata.

        Returns:
            ScannerInfo: Scanner version and implementation details.
        """
        return ScannerInfo(
            version=__version__,
            database_version=str(DATABASE_VERSION),
        )

    def close(self) -> None:
        """Release scanner resources."""
        self._closed = True

    def __enter__(self) -> OCRScanner:
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Context manager exit."""
        self.close()
