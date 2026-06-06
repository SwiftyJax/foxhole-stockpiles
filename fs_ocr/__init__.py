"""fs_ocr - Foxhole Stockpile OCR Module.

This package provides OCR functionality for extracting item data from
Foxhole game stockpile screenshots.

Public API:
    OCRScanner: Main scanner class for analyzing stockpile images.
    ScannerConfig: Configuration for the scanner.
    ScannerInfo: Metadata about the scanner.
    Stockpile: Result model (re-exported from foxhole_stockpiles.models).
    StockpileItem: Item model (re-exported from foxhole_stockpiles.models).
    SCHEMA_VERSION: Current API schema version.

Example:
    from fs_ocr import OCRScanner, ScannerConfig
    from pathlib import Path

    config = ScannerConfig(database_path=Path("data/templates.h5"))
    with OCRScanner(config) as scanner:
        result = await scanner.scan(Path("screenshot.png"))
        for item in result.items:
            print(f"{item.code}: {item.quantity}")
"""

from foxhole_stockpiles.models.stockpile import Stockpile
from foxhole_stockpiles.models.stockpile_item import StockpileItem
from fs_ocr.api import (
    SCHEMA_VERSION,
    OCRScanner,
    ScannerConfig,
    ScannerInfo,
)

__all__ = [
    "OCRScanner",
    "ScannerConfig",
    "ScannerInfo",
    "Stockpile",
    "StockpileItem",
    "SCHEMA_VERSION",
]
