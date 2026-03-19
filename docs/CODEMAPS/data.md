# Data Models & Database Schema

**Last Updated:** 2026-03-19

## Data Models Overview

All models use Pydantic v2 with strict validation and JSON serialization support.

### Core Output Models

#### Stockpile (Main Result)
**File:** `/foxhole_stockpiles/models/stockpile.py`

```python
class Stockpile(BaseModel):
    name: str                                  # Stockpile name (player-given or type)
    type: StockpileType                        # Enum: 11 types
    items: list[StockpileItem] = Field(...)   # Detected items
    timestamp: datetime                        # Processing timestamp
    shard: str                                 # Server shard (ABLE, BAKER, etc.)
    ingame_timestamp: str                      # In-game time from screenshot
    resolution: str | None                     # Source resolution (e.g., "1920x1080")
    errors: list[str]                          # Processing errors/warnings

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        return value.isoformat()
```

**JSON Example:**
```json
{
  "name": "Logi Base",
  "type": "Seaport",
  "items": [...],
  "timestamp": "2026-03-19T10:30:00Z",
  "shard": "ABLE",
  "ingame_timestamp": "Day 1293, 19:06 Hours",
  "resolution": "1920x1080",
  "errors": []
}
```

#### StockpileItem (Individual Item)
**File:** `/foxhole_stockpiles/models/stockpile_item.py`

```python
class StockpileItem(BaseModel):
    code: str                      # Item code (e.g., "8MASS")
    quantity: str                  # OCR-extracted quantity (e.g., "450")
    confidence: float              # Template match confidence (0.0-1.0)
    faction: ItemFaction | None    # Colonial or Warden (or null)
    category: ItemCategory | None  # Item category (Ammo, Weapons, etc.)
    crated: bool                   # True if crate overlay was detected
    resolution: SupportedResolution # Template resolution (664px, 1008px, etc.)
```

**JSON Example:**
```json
{
  "code": "8MASS",
  "quantity": "450",
  "confidence": 0.987,
  "faction": "Warden",
  "category": "Ammo",
  "crated": false,
  "resolution": "1920px"
}
```

### Supporting Models

#### ScanResult (API Response Envelope)
**File:** `/foxhole_stockpiles/models/scan_result.py`

```python
class ScanResult(BaseModel):
    success: bool                  # True if processing succeeded
    data: Stockpile | None         # Result (null on error)
    error: str | None              # Error message (null on success)
    processing_time_ms: float      # Total processing duration
```

#### CatalogItem (Item Metadata)
**File:** `/foxhole_stockpiles/models/catalog_item.py`

```python
class CatalogItem(BaseModel):
    code: str                      # Unique item code
    name: str                      # Display name
    category: ItemCategory         # Category enum
    faction: ItemFaction | None    # Colonial/Warden (null = neutral)
    cratable: bool                 # Can appear in crate form
    icon_hash: str                 # Icon identifier
    description: str               # Item description
```

#### MatchResult (Template Matching)
**File:** `/foxhole_stockpiles/models/match_result.py`

```python
class MatchResult(BaseModel):
    code: str                      # Item code from template
    ncc_score: float               # Normalized Cross-Correlation score
    phash_distance: int            # pHash Hamming distance
    resolution: SupportedResolution # Template resolution
    mod: str                       # Template mod name
    crated: bool                   # Crate overlay applied
```

#### ItemCandidate (Icon Detection)
**File:** `/foxhole_stockpiles/models/item_candidate.py`

```python
class ItemCandidate(BaseModel):
    image: NDArray[np.uint8]       # Extracted icon image
    position: tuple[int, int]      # (x, y) position in original
    group_index: int               # Group number
    slot_index: int                # Index within group
    matches: list[MatchResult]     # Top template matches
```

#### IconTemplate (Template Metadata)
**File:** `/foxhole_stockpiles/models/icon_template.py`

```python
class IconTemplate(BaseModel):
    image: NDArray[np.uint8]       # Pre-scaled image data
    code: str                      # Item code
    faction: ItemFaction           # Colonial/Warden
    category: ItemCategory         # Item category
    mod: str                       # Mod name (vanilla, airborne, etc.)
    crated: bool                   # Crate overlay applied
    resolution: SupportedResolution # Template resolution
    phash: int                     # Perceptual hash (uint64)
```

#### DatabaseStatistics
**File:** `/foxhole_stockpiles/models/database_statistics.py`

```python
class DatabaseStatistics(BaseModel):
    total_templates: int
    total_mods: int
    mod_stats: dict[str, dict[str, int]]
    # Example mod_stats:
    # {
    #   "vanilla": {"total": 5000, "crated": 2500},
    #   "airborne": {"total": 2000, "crated": 1000}
    # }
```

## Database Schema

### HDF5 Template Database (v2)

**Format Version:** 2
**Current Format:** HDF5 (binary, queryable)
**Previous Format:** Pickle (deprecated)

**Location:** `database_path` (configurable, default: `~/.stockpiles/templates.h5`)

#### Structure
```
database.h5
├── metadata (Group)
│   ├── version (Attribute): 2
│   ├── format (Attribute): "hdf5"
│   └── created_at (Attribute): ISO timestamp
│
├── resolution_664px (Group)
│   ├── images (Dataset): (N, 664, 664, 3) uint8
│   ├── codes (Dataset): (N,) H5T_STRING
│   ├── factions (Dataset): (N,) H5T_STRING
│   ├── categories (Dataset): (N,) H5T_STRING
│   ├── mods (Dataset): (N,) H5T_STRING
│   ├── phashes (Dataset): (N,) uint64
│   └── cratable (Dataset): (N,) bool
│
├── resolution_1008px (Group)
│   └── [same structure]
│
└── resolution_2160px (Group)
    └── [same structure]
```

#### Supported Resolutions
16 resolutions available:
```
664px, 1008px, 1012px, 1024px, 1080px, 1200px, 1440px,
1536px, 1664px, 1680px, 1920px, 2048px, 2160px, 2400px,
2560px, 2880px
```

**Scaling:** All templates scaled relative to 1920px base resolution

#### Database Statistics

**Key Metrics:**
- Templates per resolution: ~5,000-6,000
- Total templates: ~80,000-96,000 (with crated variants)
- File size: ~5-10 MB (compressed HDF5)
- Mods: vanilla, airborne, and community mods

**Access Pattern:**
```python
import h5py

db = h5py.File("templates.h5", "r")

# List all resolutions
resolutions = [k for k in db.keys() if k.startswith("resolution_")]

# Access resolution group
res_group = db["resolution_1920px"]

# Get all images for a resolution
images = res_group["images"][:]          # Shape: (N, 1920, 1920, 3)
codes = res_group["codes"][:]            # Shape: (N,)
factions = res_group["factions"][:]      # Shape: (N,)
mods = res_group["mods"][:]              # Shape: (N,)
phashes = res_group["phashes"][:]        # Shape: (N,)
cratable = res_group["cratable"][:]      # Shape: (N,)
```

### Catalog JSON

**Location:** `data/fs_catalog.json`

```json
{
  "items": [
    {
      "code": "8MASS",
      "name": "8mm Ammo",
      "category": "Ammo",
      "faction": "Warden",
      "cratable": true,
      "icon_hash": "abc123def456"
    }
  ]
}
```

## Enums (Type-Safe, StrEnum)

### StockpileType
**File:** `/foxhole_stockpiles/enums/stockpile_type.py`

```python
class StockpileType(StrEnum):
    # Bases
    ENCAMPMENT = "Encampment"
    KEEP = "Keep"
    SAFE_HOUSE = "Safe House"
    RELIC_BASE = "Relic Base"
    BUNKER_BASE = "Bunker Base"
    BORDER_BASE = "Border Base"
    TOWN_BASE = "Town Base"
    UNDERGROUND_FORTRESS = "Underground Fortress"
    BMS_LONGHOOK = "BMS - Longhook"

    # Structures
    STORAGE_DEPOT = "Storage Depot"
    SEAPORT = "Seaport"
    AIRCRAFT_DEPOT = "Aircraft Depot"

    UNDEFINED = "Undefined"

    def has_custom_name(self) -> bool:
        """Only Storage Depot, Seaport, Aircraft Depot can have custom names."""
```

### ItemFaction
**File:** `/foxhole_stockpiles/enums/item_faction.py`

```python
class ItemFaction(StrEnum):
    COLONIAL = "Colonial"
    WARDEN = "Warden"
    NEUTRAL = "Neutral"
```

### ItemCategory
**File:** `/foxhole_stockpiles/enums/item_category.py`

```python
class ItemCategory(StrEnum):
    # Ammunition
    AMMO = "Ammo"
    AT_AMMO = "AT Ammo"
    # ... 18+ more categories
    VEHICLES = "Vehicles"
```

### SupportedLanguage
**File:** `/foxhole_stockpiles/enums/supported_language.py`

```python
class SupportedLanguage(StrEnum):
    ENGLISH = "en"
    PORTUGUESE = "pt"
    FRENCH = "fr"
    GERMAN = "de"
    RUSSIAN = "ru"
    CHINESE = "zh"
    # ... more languages
```

### SupportedResolution
**File:** `/foxhole_stockpiles/enums/supported_resolution.py`

```python
class SupportedResolution(StrEnum):
    RES_664 = "664px"
    RES_1008 = "1008px"
    # ... 14 more resolutions
    RES_2880 = "2880px"
```

### EventType
**File:** `/foxhole_stockpiles/enums/event_type.py`

```python
class EventType(StrEnum):
    SERVER_STARTED = "server_started"
    SERVER_STOPPED = "server_stopped"
    SCAN_STARTED = "scan_started"
    SCAN_COMPLETED = "scan_completed"
    SCAN_FAILED = "scan_failed"
    MOD_IMPORTED = "mod_imported"
```

## Configuration Models

### AppSettings (Root)
**File:** `/foxhole_stockpiles/core/settings/app_settings.py`

```python
class AppSettings(BaseSettings):
    config_version: int                    # Migration version
    api_server: APIServerSettings
    api_auth: APIAuthSettings
    external_tools: ExternalToolsSettings
    logging: LoggingSettings
    ocr: OCRSettings
    output: OutputSettings
    scanner: ScannerSettings
    stockpile_types: StockpileTypesSettings
    templates: TemplateSettings
    database_builder: DatabaseBuilderSettings
    notifications: NotificationsSettings
    gui: GUISettings
```

### ScannerSettings
**File:** `/foxhole_stockpiles/core/settings/sections/scanner.py`

```python
class ScannerSettings(BaseSettings):
    database_path: Path | None
    tessdata_path: str = "./tessdata"
    custom_model: str = "renner_numbers"
    template_cache_size: int = 16
    early_exit_threshold: float = 0.0
    confidence_gap: float = 0.0
    max_ncc_candidates: int = 25
    phash_threshold: int = 12
    ncc_tiebreaker_threshold: float = 0.002  # Pixel diff tiebreaker
    debug_mode: bool = False
    extract_icons: bool = False
```

### OutputSettings
**File:** `/foxhole_stockpiles/core/settings/sections/output.py`

```python
class OutputSettings(BaseSettings):
    handlers: list[OutputHandlerConfig]

class OutputHandlerConfig(BaseModel):
    handler: (
        ConsoleHandlerSettings |
        FileHandlerSettings |
        WebhookHandlerSettings |
        ReturnHandlerSettings
    )
    format: FormatSettings
```

## Data Flow Models

### Processing Pipeline
```
Image Input
  ↓
StockpileDetector
  ├─ scale_factor: float
  ├─ box_width/height: int
  ├─ quantities: list[Coordinates]
  └─ groups: dict[int, list[IconCandidate]]
  ↓
TemplateManager
  ├─ resolution: SupportedResolution
  ├─ candidates: list[MatchResult]
  └─ conflicts: dict[ItemCandidate, list[MatchResult]]
  ↓
StockpileTextExtractor
  ├─ quantity_image: NDArray
  └─ extracted_text: str
  ↓
Stockpile Model
  ├─ items: list[StockpileItem]
  ├─ errors: list[str]
  └─ metadata: ...
```

## Query Patterns

### Filter Templates by Faction
```python
db = TemplateDatabase(resolution=SupportedResolution.RES_1920)
candidate_indices = db.get_candidates(
    faction=ItemFaction.WARDEN
)
# Returns: [0, 5, 12, 18, ...] (indices in db.templates)
```

### Filter Templates by Faction + Mod
```python
candidate_indices = db.get_candidates(
    faction=ItemFaction.WARDEN,
    mod="vanilla"
)
```

### Find by Item Code
```python
candidate_indices = db.get_candidates(
    code="8MASS"
)
```

## JSON Serialization

**Configuration:**
```python
model_config = ConfigDict(
    extra="forbid",                    # No unknown fields
    use_enum_values=True,              # Serialize enums as strings
    json_schema_extra={...}            # Add examples
)
```

**Example Serialization:**
```python
stockpile = Stockpile(name="Logi", type=StockpileType.SEAPORT, ...)
json_str = stockpile.model_dump_json(indent=2)
# Output: {"name": "Logi", "type": "Seaport", ...}
```

## Key Files

1. `/foxhole_stockpiles/models/stockpile.py` - Main output model
2. `/foxhole_stockpiles/models/stockpile_item.py` - Item details
3. `/foxhole_stockpiles/services/template_database.py` - HDF5 access
4. `/foxhole_stockpiles/core/settings/app_settings.py` - Configuration model
5. `/foxhole_stockpiles/enums/` - All type-safe enums
