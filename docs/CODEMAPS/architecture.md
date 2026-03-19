# Architecture & Design Patterns

**Last Updated:** 2026-03-19

## System Design Philosophy

1. **Service Layer Pattern** - Business logic in focused service classes
2. **Dependency Injection** - Constructor injection, no global state
3. **Multi-handler Output** - Route results to multiple destinations simultaneously
4. **Event-Driven Notifications** - Decoupled via EventBus
5. **Configuration as Code** - Pydantic settings with environment overrides

## Core Orchestration: OCRCoordinator

**Location:** `/foxhole_stockpiles/services/ocr_coordinator.py`

```python
class OCRCoordinator:
    def __init__(
        self,
        config: ScannerSettings,
        event_bus: EventBus | None = None
    ) -> None:
        self._text_extractor = StockpileTextExtractor(...)
        self._template_manager = TemplateManager(...)
        self._stockpile_type_classifier = StockpileTypeClassifier()

    async def scan_stockpile(
        self,
        image: NDArray[np.uint8],
        faction: ItemFaction | None = None,
        language: SupportedLanguage | None = None,
        mods: list[str] | None = None,
    ) -> Stockpile:
        """Main entry point for image scanning."""
        # 1. Detect stockpile type and components
        # 2. Match icons to templates
        # 3. Extract quantities via OCR
        # 4. Resolve conflicts and duplicates
        # 5. Return Stockpile model
```

**Key Methods:**
- `scan_stockpile()` - Main pipeline orchestrator
- `_detect_stockpile_type()` - NLP-based type classification
- `_process_icon_candidate()` - Icon matching and conflict resolution
- `_extract_icon_to_folder()` - Debug icon export

## Component Responsibilities

### 1. StockpileDetector (Visual Geometry)
**File:** `/foxhole_stockpiles/services/stockpile_detector.py`

**Responsibility:** Identify visual components in screenshots

**Key Attributes:**
```python
class StockpileDetector:
    scale_factor: float         # Resolution scaling (base 1920px)
    box_width/height: int       # Icon dimensions
    quantities: list[Coordinates]  # (x, y) of quantity boxes
    groups: dict[int, list[...]]  # Grouped icon positions
```

**Algorithm:**
1. Analyze image dimensions → calculate scale factor
2. Detect binary threshold → find contours
3. Identify quantity box patterns
4. Group icons by proximity
5. Extract region boundaries

### 2. TemplateManager (Icon Matching)
**File:** `/foxhole_stockpiles/services/template_manager.py`

**Responsibility:** Match detected icons to known templates

**Two-Phase Matching + Tiebreaker:**
```python
# Phase 1: Fast pHash filtering
candidates = db.get_candidates(
    faction=faction,
    mod=mod,
    category=category,
    excluded_codes=excluded
)

# Phase 2: Precise NCC scoring
matches = [
    MatchResult(code, ncc_score, resolution, phash_distance)
    for template in candidates
    if phash_distance < threshold
    if ncc_score > min_threshold
]
matches.sort(key=lambda m: m.ncc_score, reverse=True)

# Phase 3 (optional): NCC Tiebreaker
# When top matches are within ncc_tiebreaker_threshold (default 0.0015),
# use mean pixel difference to distinguish similar items
# (e.g., Assembly Materials V vs VIII)
```

**Conflict Resolution:**
- Duplicate detection: Same item in multiple groups
- Group-level resolution: Find optimal non-overlapping assignment
- Confidence-based ranking: NCC score determines final selection

### 3. StockpileTextExtractor (OCR)
**File:** `/foxhole_stockpiles/services/stockpile_text_extractor.py`

**Responsibility:** Extract and recognize quantities from images

**Pipeline:**
```python
def extract_text(self, image: NDArray[np.uint8]) -> str:
    # 1. Apply binary threshold (Otsu)
    # 2. Noise reduction (morphological ops)
    # 3. Tesseract OCR (custom model: renner_numbers.traineddata)
    # 4. Regex parsing: extract numeric values
    # 5. Return quantity string
```

**Configuration:**
- `tessdata_path` - Path to Tesseract training data
- `custom_model` - Enable custom number model
- `binary_threshold` - 127 (hardcoded in OCRCoordinator)
- `language` - Configurable (en, pt, fr, de, ru, zh, etc.)

### 4. StockpileTypeClassifier (NLP)
**File:** `/foxhole_stockpiles/services/stockpile_type_classifier.py`

**Responsibility:** Identify stockpile type from screenshot text

**Algorithm:** Text pattern matching against stockpile type strings

**Input:** Stockpile name text extracted from UI
**Output:** `StockpileType` enum

### 5. OutputCoordinator (Multi-Handler Routing)
**File:** `/foxhole_stockpiles/services/output_coordinator.py`

**Responsibility:** Route results to multiple destinations

**Handler Types:**
- `ConsoleOutputHandler` - Print to stdout
- `FileOutputHandler` - Write JSON/CSV/TSV
- `WebhookOutputHandler` - POST to external HTTP endpoint
- `ReturnOutputHandler` - Return in API response

**Execution Model:**
```python
async def handle_output(self, stockpile: Stockpile) -> dict | None:
    for handler_config in self.output_settings.handlers:
        handler = self._create_handler(handler_config)
        result = await handler.handle(
            stockpile,
            format=handler_config.format
        )
        if result is not None:
            return result  # First non-None result wins
```

## Settings Architecture

**Location:** `/foxhole_stockpiles/core/settings/`

```python
class AppSettings(BaseSettings):
    config_version: int
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

**Configuration Sources (Priority):**
1. Pydantic defaults
2. JSON file (`~/.fs_config`)
3. Environment variables (`FS_*`)

**Example Environment Variable:**
```bash
FS_SCANNER__DATABASE_PATH=/path/to/db.h5
FS_API_SERVER__HOST=0.0.0.0
FS_API_SERVER__PORT=8000
FS_NOTIFICATIONS__ENABLED=true
```

## Event System

**Location:** `/foxhole_stockpiles/core/events.py`

**Purpose:** Decouple notifications from processing pipeline

```python
class EventBus:
    def emit(self, event_type: EventType, data: dict) -> None:
        """Emit event to all subscribers."""

    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        """Register event handler."""
```

**Event Types:**
- `SERVER_STARTED` - Server initialization complete
- `SERVER_STOPPED` - Server shutdown
- `SCAN_STARTED` - Image processing begun
- `SCAN_COMPLETED` - Results ready
- `SCAN_FAILED` - Error during processing

**Subscribers:**
- NotificationService - Discord webhooks
- Logging - Structured logs
- Metrics - Memory monitoring

## Template Database Format

**Location:** `/foxhole_stockpiles/services/template_database.py`

**HDF5 Structure (v2):**
```
database.h5
├── resolution_664
│   ├── images (N, 664, 664, 3) uint8
│   ├── codes (N,) string
│   ├── factions (N,) string
│   ├── mods (N,) string
│   ├── categories (N,) string
│   ├── phashes (N,) uint64
│   └── cratable (N,) bool
├── resolution_1008
│   └── [same structure]
└── ... (14 more resolutions)
```

**Lookup Optimization:**
- Faction lookup: `dict[str, set[int]]` - O(1) faction filtering
- Mod lookup: `dict[str, set[int]]` - O(1) mod filtering
- Category lookup: `dict[str, set[int]]` - O(1) category filtering
- pHash array: Vectorized distance computation

## API Response Pattern

**Envelope Model:** `ScanResult`
```python
class ScanResult(BaseModel):
    success: bool
    data: Stockpile | None
    error: str | None
    processing_time_ms: float
```

**Example:**
```json
{
  "success": true,
  "data": {
    "name": "Logi",
    "type": "Seaport",
    "items": [
      {
        "code": "8MASS",
        "quantity": 450,
        "name": "8mm Ammo",
        "faction": "Wardens"
      }
    ],
    "timestamp": "2026-03-19T10:30:00Z"
  },
  "error": null,
  "processing_time_ms": 245.5
}
```

## Error Handling Strategy

**Validation at Boundaries:**
- Input image validation (size, format)
- Configuration validation (Pydantic)
- Database existence checks

**Error Propagation:**
- Service layer raises specific exceptions
- API converts to HTTP status codes
- Detailed logs on server side
- User-friendly messages in UI

**Critical Errors:**
- Tesseract not found → 503 Server Error
- Database not accessible → 503 Server Error
- Invalid auth → 401 Unauthorized
- Rate limit exceeded → 429 Too Many Requests

## Design Decisions

### Why Two-Phase Template Matching + Tiebreaker?
- **Phase 1 (pHash):** Fast similarity filter, eliminates 95%+ of candidates
- **Phase 2 (NCC):** Precise scoring, expensive computation on small subset
- **Phase 3 (Tiebreaker):** When NCC scores are within threshold, use pixel diff
- **Result:** Sub-second matching for 5000+ templates per resolution

### Why HDF5 over Pickle?
- **Pickle:** Monolithic, version-specific, security issues
- **HDF5:** Structured, queryable, language-agnostic, binary efficiency
- **Trade-off:** Slightly larger file size, better portability

### Why EventBus?
- **Tight Coupling:** Direct method calls → testing nightmare
- **EventBus:** Decoupled, multiple subscribers, async notifications
- **Use Cases:** Discord webhooks, logging, metrics, monitoring

### Why Multiple Output Handlers?
- **Single Handler:** Hardcoded output format
- **Multiple Handlers:** Same result → console + file + webhook
- **Priority:** First non-None response returned to API client

---

## Dataflow Diagram

```
USER/CLIENT
    ↓
┌──────────────────────────┐
│ FastAPI Server           │
│ POST /ocr/scan_image     │
└──────────────────────────┘
    ↓
┌──────────────────────────┐
│ Request Validation       │
│ (Auth, Rate Limit)       │
└──────────────────────────┘
    ↓
┌──────────────────────────┐
│ OCRCoordinator.scan()    │
├──────────────────────────┤
│ 1. StockpileDetector     │ ← Detect visual components
│ 2. TemplateManager       │ ← Match icons
│ 3. TextExtractor         │ ← Extract quantities
│ 4. TypeClassifier        │ ← Identify type
│ 5. Conflict Resolution   │ ← Deduplicate items
└──────────────────────────┘
    ↓
┌──────────────────────────┐
│ OutputCoordinator        │
├──────────────────────────┤
│ ┌─ ConsoleHandler        │
│ ├─ FileHandler           │
│ └─ WebhookHandler        │
└──────────────────────────┘
    ↓
┌──────────────────────────┐
│ API Response             │
│ ScanResult(Stockpile)    │
└──────────────────────────┘
    ↓
CLIENT/USER
```

## Key Files for Understanding Architecture

1. `/foxhole_stockpiles/api/server.py` - FastAPI setup
2. `/foxhole_stockpiles/services/ocr_coordinator.py` - Main orchestration
3. `/foxhole_stockpiles/core/settings/app_settings.py` - Configuration
4. `/foxhole_stockpiles/services/template_manager.py` - Icon matching
5. `/foxhole_stockpiles/services/output_coordinator.py` - Output routing
