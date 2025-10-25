"""Settings sections exports."""

from foxhole_stockpiles.core.settings.sections.api import APIAuthSettings, APIServerSettings
from foxhole_stockpiles.core.settings.sections.logging import LoggingSettings
from foxhole_stockpiles.core.settings.sections.ocr import OCRSettings
from foxhole_stockpiles.core.settings.sections.output import (
    ConsoleOutputSettings,
    FileOutputSettings,
    OutputSettings,
    WebhookOutputSettings,
)
from foxhole_stockpiles.core.settings.sections.scanner import ScannerSettings
from foxhole_stockpiles.core.settings.sections.stockpile_types import StockpileTypesSettings
from foxhole_stockpiles.core.settings.sections.templates import TemplateSettings

__all__ = [
    "APIAuthSettings",
    "APIServerSettings",
    "ConsoleOutputSettings",
    "FileOutputSettings",
    "LoggingSettings",
    "OCRSettings",
    "OutputSettings",
    "ScannerSettings",
    "StockpileTypesSettings",
    "TemplateSettings",
    "WebhookOutputSettings",
]
