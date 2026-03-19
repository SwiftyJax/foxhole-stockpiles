# Foxhole Stockpiles - Codemap Index

**Last Updated:** 2026-03-19
**Version:** 0.4.0
**Language:** Python 3.12+

## Project Overview

Foxhole Stockpiles is a computer vision and OCR system that extracts structured item data from Foxhole game screenshots. It processes stockpile UI screenshots through a multi-stage pipeline: detection → icon matching → quantity recognition → formatted output.

### Key Statistics
- **Services:** 12 core services + 4 notifiers/handlers
- **Resolutions:** 16 supported screen resolutions (664px to 2160px)
- **Database:** HDF5 template storage (v2 format)
- **CLI Commands:** 11 distinct subcommands
- **Frameworks:** FastAPI, PyQt6, Click, Pydantic v2

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     ENTRY POINTS                            │
├──────────────────┬──────────────────┬──────────────────┐
│  CLI (fs tool)   │  FastAPI Server  │   PyQt6 GUI     │
│  11 commands     │  /ocr/scan_image │  Desktop App    │
└──────────────────┴──────────────────┴──────────────────┘
          │                  │                   │
          └──────────────────┼───────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────────┐
│            CORE PROCESSING PIPELINE                          │
├────────────────┬────────────────┬────────────────┬─────────┐
│ StockpileType  │ Stockpile      │ Template       │ Output  │
│ Classifier     │ Detector       │ Manager        │ Handler │
├────────────────┼────────────────┼────────────────┼─────────┤
│ NLP text       │ Box detection  │ Icon matching  │ JSON    │
│ classification │ Geometry calc  │ NCC scoring    │ CSV/TSV │
│                │ Quantity boxes │ Faction filter │ Webhook │
└────────────────┴────────────────┴────────────────┴─────────┘
                             ↓
┌──────────────────────────────────────────────────────────────┐
│         EXTERNAL DEPENDENCIES & DATA SOURCES                 │
├──────────────────┬──────────────────┬──────────────────┐
│ OpenCV (4.13+)   │ Tesseract OCR    │ Catalog Service │
│ Image processing │ Text extraction  │ Item metadata   │
└──────────────────┴──────────────────┴──────────────────┘
```

## Core Modules

### 1. **api/** - FastAPI Server & Web Interface
- **server.py** - FastAPI app initialization, routes, middleware
- **dependencies.py** - Dependency injection for services
- **auth.py** - API authentication (None/Bearer/API-Key)
- **web/routes.py** - Web UI endpoints (HTML form upload)
- **memory_middleware.py** - Memory monitoring middleware

**Key Routes:**
- `POST /ocr/scan_image` - Main OCR endpoint (rate limited 30/min)
- `GET /health` - Health check
- `GET /` - Web UI
- `POST /web/scan` - Web form submission

### 2. **services/** - Business Logic Layer
Core orchestrators and utilities:
- **ocr_coordinator.py** - Main orchestrator (detection→matching→OCR→output)
- **stockpile_detector.py** - Visual component detection
- **template_manager.py** - Icon template database management
- **stockpile_text_extractor.py** - Tesseract OCR wrapper
- **template_database.py** - HDF5 storage access (16 resolutions)
- **output_coordinator.py** - Multi-handler output routing
- **catalog_service.py** - Item metadata lookup
- **notification_service.py** - Event notifications (Discord, etc.)
- **stockpile_type_classifier.py** - NLP-based stockpile type detection
- **icon_manager.py** - Icon image extraction
- **memory_monitor.py** - Memory usage tracking

### 3. **commands/** - CLI Commands
Unified CLI dispatcher with subcommands:
- **fs/fs.py** - CLI dispatcher (main entry point)
- **stockpile_scanner/stockpile_scanner.py** - `fs scanner` - scan images
- **api_server/api_server.py** - `fs server` - start FastAPI server
- **database_builder/database_builder.py** - `fs build-db` - compile templates
- **generate_templates/generate_templates.py** - `fs gen-templates` - create templates
- **catalog_builder/catalog_builder.py** - `fs build-catalog` - build item catalog
- **uasset_extractor/uasset_extractor.py** - `fs extract-assets` - extract game assets
- **add_mod/add_mod.py** - `fs add-mod` - import new mod into database
- **add_icon/add_icon.py** - `fs add-icon` - add single icon
- **candidate_inspector/candidate_inspector.py** - `fs inspect` - debug matching
- **gui/gui.py** - `fs-gui` - launch PyQt6 desktop application
- **update_config/update_config.py** - `fs config` - config management

### 4. **models/** - Data Models (Pydantic v2)
Request/response and internal models:
- **stockpile.py** - `Stockpile` - complete result model
- **stockpile_item.py** - `StockpileItem` - individual item + quantity
- **catalog_item.py** - `CatalogItem` - item metadata from catalog
- **match_result.py** - `MatchResult` - template matching result
- **item_candidate.py** - `ItemCandidate` - detected icon candidate
- **icon_template.py** - `IconTemplate` - template metadata
- **scan_result.py** - API response envelope
- **database_statistics.py** - Template database stats
- **memory_snapshot.py** - Memory monitoring data

### 5. **core/** - Configuration & Utilities
- **settings/app_settings.py** - Main Pydantic settings (v5 format)
- **settings/sections/** - Nested config sections (scanner, api, notifications, etc.)
- **events.py** - Centralized EventBus for notifications
- **logging.py** - Structured logging setup
- **utils.py** - Common utilities (path resolution, image ops)
- **version.py** - Version info

### 6. **enums/** - Type-Safe Enums (StrEnum)
- **stockpile_type.py** - 11 stockpile types (bases, structures, undefined)
- **item_faction.py** - Colonials/Wardens
- **item_category.py** - 20+ item categories
- **supported_language.py** - OCR languages (en, pt, fr, de, ru, zh, etc.)
- **supported_resolution.py** - 16 screen resolutions
- **auth_type.py** - Authentication types
- **event_type.py** - Event types for notifications
- **output_format.py** - JSON/CSV/TSV
- **notifier_type.py** - Discord, webhook types

### 7. **handlers/** - Output Routing
Multiple output destinations:
- **base_handler.py** - `BaseOutputDestinationHandler` interface
- **console.py** - `ConsoleOutputHandler` - CLI output
- **file.py** - `FileOutputHandler` - JSON/CSV/TSV files
- **webhook.py** - `WebhookOutputHandler` - HTTP POST
- **response.py** - `ReturnOutputHandler` - API response

### 8. **notifiers/** - Event Notifications
- **base.py** - `BaseNotifier` interface
- **discord.py** - `DiscordNotifier` - Discord webhook notifications

### 9. **gui/** - PyQt6 Desktop Application
- **app.py** - Main window and orchestration
- **widgets/** - Reusable UI components
- **config_tabs/** - Configuration interface tabs

### 10. **i18n/** - Internationalization
- Translation and localization utilities

### 11. **connectors/** - External Service Integration
- Tool interaction (repak, umodel)

## Data Flow

### Scanning Pipeline
```
1. Image Input (PNG/JPG)
   ↓
2. [StockpileDetector]
   - Detect stockpile type region
   - Detect icon box positions
   - Extract icon images
   - Locate quantity boxes
   ↓
3. [TemplateManager + TemplateDatabase]
   - Filter by resolution, faction, mod
   - pHash similarity filter
   - NCC (Normalized Cross-Correlation) matching
   - Return top matches per position
   ↓
4. [StockpileTextExtractor]
   - Extract quantity box images
   - Apply OCR via Tesseract
   - Parse numbers with regex
   ↓
5. [OutputCoordinator]
   - Format results (JSON/CSV/TSV)
   - Route to handlers (console/file/webhook)
   - Return API response
   ↓
6. Output (Stockpile model with items list)
```

## Configuration System

**Priority Order:**
1. Environment variables (`FS_*` prefix, `__` for nesting)
2. JSON config file (`~/.fs_config`)
3. Pydantic defaults

**Example:**
```python
# Env: FS_SCANNER__DATABASE_PATH=/path/to/db.h5
# JSON: {"scanner": {"database_path": "/path/to/db.h5"}}
# Config: AppSettings.scanner.database_path
```

## Database Format

**HDF5 Template Database (v2):**
- Structure: Group per resolution (664px, 1008px, ..., 2160px)
- Each group contains: image arrays, metadata (code, faction, mod, category, crated)
- Two-phase matching: pHash filter → NCC scoring
- Supports multiple mods (vanilla, airborne, etc.)

## Related Documentation

- **architecture.md** - Detailed system design and patterns
- **backend.md** - API routes, middleware, service layer
- **data.md** - Database schema, models, HDF5 structure
- **dependencies.md** - External tools and libraries

---

**Key Files to Understand the System:**
1. `/foxhole_stockpiles/api/server.py` - Entry point
2. `/foxhole_stockpiles/services/ocr_coordinator.py` - Core pipeline
3. `/foxhole_stockpiles/models/stockpile.py` - Output model
4. `/foxhole_stockpiles/core/settings/app_settings.py` - Configuration
5. `/foxhole_stockpiles/commands/fs/fs.py` - CLI dispatcher
