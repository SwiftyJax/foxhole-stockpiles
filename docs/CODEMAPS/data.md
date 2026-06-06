<!-- Generated: 2026-06-06 | Branch: refactor/01-pyside6 | Token estimate: ~900 -->

# Data Models, Config & Database

All models are Pydantic v2, strict validation, JSON-serializable. Enums are `StrEnum`.

## Core output models

### Stockpile (`models/stockpile.py`)
```python
class Stockpile(BaseModel):
    name: str                  # stockpile name (player-given or type)
    type: StockpileType        # enum (11 + Undefined)
    items: list[StockpileItem]
    timestamp: datetime        # serialized ISO
    shard: str                 # server shard (ABLE, BAKER, ...)
    ingame_timestamp: str      # in-game time from screenshot
    resolution: str | None
    errors: list[str]
```

### StockpileItem (`models/stockpile_item.py`)
```python
class StockpileItem(BaseModel):
    code: str
    quantity: str              # OCR-extracted
    confidence: float          # NCC match 0..1
    faction: ItemFaction | None
    category: ItemCategory | None
    crated: bool
    resolution: SupportedResolution
```

### Other runtime models (`models/`)
- `scan_result.py` `ScanResult` — API envelope `{success, data, error, processing_time_ms}`
- `catalog_item.py` `CatalogItem` — item metadata (`cratable`, faction, category, icon)
- `match_result.py` `MatchResult` — `{code, ncc_score, phash_distance, resolution, mod, crated}`
- `item_candidate.py` `ItemCandidate` — detected icon (image, position, group/slot, matches)
- `icon_template.py` `IconTemplate` — template (image, code, faction, category, mod, crated, resolution, phash)
- `database_statistics.py`, `detected_icon_info.py`, `stockpile_coords.py`, `stockpile_image_regions.py`
- `memory_snapshot.py`, `request_memory_stats.py` — memory monitoring
- `mod_import_config.py`, `mod_import_progress.py`, `mod_import_result.py`, `pak_validation_result.py` — mod/asset import (uses `TemplateSettings`)
- `notification.py`, `command_info.py`

### fs_ocr public models (`fs_ocr/api.py`)
```python
class ScannerConfig(BaseModel):       # engine input
    database_path: Path
    tessdata_path: str = "tessdata"
    custom_model: str = "renner_numbers"
    template_cache_size: int = 16
    early_exit_threshold: float = 0.0
    confidence_gap: float = 0.0
    extract_icons: bool = False

class ScannerInfo(BaseModel):
    schema_version: Literal["1"] = "1"
    implementation: Literal["python", "rust"] = "python"
    version: str
    database_version: str | None
```
`__all__`: `OCRScanner, ScannerConfig, ScannerInfo, Stockpile, StockpileItem, SCHEMA_VERSION`.

## Enums (`enums/`)

| Enum | Values |
|---|---|
| `StockpileType` | 11 types (Encampment, Keep, Safe House, Relic/Bunker/Border/Town Base, Underground Fortress, BMS-Longhook, Storage Depot, Seaport, Aircraft Depot) + Undefined |
| `ItemFaction` | Colonial, Warden, Neutral |
| `ItemCategory` | 20+ (Ammo, AT Ammo, Weapons, … Vehicles) |
| `SupportedLanguage` | en, pt, fr, de, ru, zh, … |
| `SupportedResolution` | 16 (664px … 2880px) |
| `OutputFormat` | JSON, CSV, TSV |
| `OutputDestination` / `OutputHandlerType` | console, file, webhook, response |
| `AuthType` | none, bearer, api_key |
| `EventType` | server/scan lifecycle + mod_imported |
| `ConfigLevel`, `NotifierType` | config scope, notifier kinds |

## Configuration (`core/settings/`)

### AppSettings root (schema **v8**)
```python
class AppSettings(BaseSettings):
    config_version: int        # CURRENT_VERSION = 8
    api_server: APIServerSettings
    api_auth: APIAuthSettings
    external_tools: ExternalToolsSettings
    logging: LoggingSettings
    output: OutputSettings
    scanner: ScannerSettings
    stockpile_types: StockpileTypesSettings
    database_builder: DatabaseBuilderSettings
    notifications: NotificationsSettings
    gui: GUISettings
    sav_processing: SavProcessingSettings
```
Sub-section files also include `ocr.py` (`OCRSettings`, consumed by
`fs_ocr/_impl/detector.py`) and `templates.py` (`TemplateSettings`, used by mod
import) — these are nested/consumer models, not top-level fields.

### ScannerSettings (`sections/scanner.py`)
`database_path`, `template_cache_size`, `early_exit_threshold`,
`confidence_gap`, `debug_mode`, `extract_icons`, `screenshots_folder`.
(v8 dropped the formerly-configurable `custom_model`, `tessdata_path`,
`max_ncc_candidates`, `phash_threshold`, `ncc_tiebreaker_threshold` — now fixed
defaults. The OCR engine still receives `tessdata_path`/`custom_model` via
`fs_ocr.api.ScannerConfig`, but they are no longer user settings.)

### OutputSettings (`sections/output/`)
`OutputSettings.handlers: list[HandlerConfig]`; per-handler models in
`output/`: `console_handler.py`, `file_handler.py`, `webhook_handler.py`,
`return_handler.py`, plus format models `json_format.py`, `csv_format.py`.

### Sources & migration
Priority: env `FS_<SECTION>__<KEY>` → JSON file (platform config dir,
`json_settings_source.py`) → defaults. Stepwise upgrade in
`config_migrator.py` (v1 → … → 8).

## Template database (HDF5, v2)

`fs_ocr/_impl/template_database.py`. Default `database_path` configurable.

```
database.h5
├── metadata        {version:2, format:"hdf5", created_at}
├── resolution_664px
│   ├── images      (N, H, W, 3) uint8
│   ├── codes        (N,) string
│   ├── factions     (N,) string
│   ├── categories   (N,) string
│   ├── mods         (N,) string
│   ├── phashes      (N,) uint64
│   └── cratable     (N,) bool
└── ... 15 more resolution groups (664px … 2880px)
```

- All templates scaled relative to 1920px base.
- O(1) faction/mod/category index sets for prefiltering; vectorized pHash distance.
- Multi-mod (vanilla, airborne, community). Built by `fs-tools`.

## Catalog JSON (`data/catalog.json`)

Item metadata: `code`, `name`, `category`, `faction`, `cratable`, icon ref.
`cratable` ← `ItemProfileData.bIsCratable` (items) or presence of
`MassProductionFactory` in `ProductionCategories` (vehicles).

## SAV data

Parsed via `services/sav_parser.py` → `fs-sav` (Rust). Produces faction-tagged
dicts with Z/ns timestamps; NOT validated through `Stockpile`.

## Key files
1. `models/stockpile.py`, `models/stockpile_item.py`
2. `fs_ocr/api.py` — engine I/O models
3. `fs_ocr/_impl/template_database.py` — HDF5 access
4. `core/settings/app_settings.py` + `config_migrator.py`
5. `enums/` — type-safe enums
