# Configuration Guide

The Foxhole Stockpile Scanner can be configured using environment variables or a configuration file.

## Configuration Methods

### 1. Environment Variables

Environment variables use the prefix `FS_` and nested settings are separated by `__`:

```bash
# API Authentication
export FS_API_AUTH__AUTH_TYPE=bearer
export FS_API_AUTH__AUTH_TOKEN=your-secret-token

# Scanner settings
export FS_SCANNER__DATABASE_PATH=/path/to/database.pkl
export FS_SCANNER__FACTION_FILTER=colonials

# Output format
export FS_OUTPUT_FORMAT__OUTPUT_FORMAT=webhook
export FS_OUTPUT_FORMAT__WEBHOOK_URL=https://example.com/webhook

# Logging
export FS_LOGGING__LOG_LEVEL=DEBUG
export FS_LOGGING__LOG_FILE=/var/log/foxhole-scanner.log
```

### 2. Configuration File

Create a file at `~/.fs_config` with JSON configuration:

```json
{
  "api_server": {
    "cors_allow_origins": ["*"]
  },
  "api_auth": {
    "auth_type": "bearer",
    "auth_token": "your-secret-token"
  },
  "scanner": {
    "database_path": "/path/to/database.pkl",
    "faction_filter": null,
    "screenshots_folder": ""
  },
  "output_format": {
    "output_format": "json",
    "file_path": "output.json",
    "webhook_url": null,
    "webhook_auth_type": null,
    "webhook_token": null,
    "webhook_client_auth_header": null
  },
  "logging": {
    "log_level": "INFO",
    "log_format": "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "rotate_logs": false,
    "log_file": null,
    "loggers": {}
  },
  "ocr": {
    "height": 2160,
    "box_width": 84,
    "box_height": 64,
    "column_offset": 112,
    "row_offset": 78,
    "group_offset": 98,
    "title_margin": 24,
    "title_min_width": 600,
    "title_height": 64,
    "icon_to_quantity_offset": 88,
    "gray_lower": 15,
    "gray_upper": 98,
    "pixel_diff_tolerance": 2
  },
  "templates": {
    "crate_blue_multiplier": 145,
    "crate_blue_offset": 82,
    "crate_green_multiplier": 152,
    "crate_green_offset": 87,
    "crate_red_multiplier": 154,
    "crate_red_offset": 89
  }
}
```

## Configuration Sections

### API Server (`api_server`)

Settings for the API server.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `cors_allow_origins` | array[string] | `["*"]` | List of allowed CORS origins. Use `["*"]` to allow all origins |
| `host` | string | `"127.0.0.1"` | Server bind host address |
| `port` | integer | `8000` | Server bind port (1-65535) |
| `workers` | integer | `1` | Number of worker processes |
| `reload` | boolean | `false` | Enable auto-reload on code changes (development only) |
| `log_level` | string | `"info"` | Server log level (`"debug"`, `"info"`, `"warning"`, `"error"`) |

**Examples:**
```bash
# Allow all origins (development)
export FS_API_SERVER__CORS_ALLOW_ORIGINS='["*"]'

# Allow specific origins (production)
export FS_API_SERVER__CORS_ALLOW_ORIGINS='["https://yourdomain.com","https://app.yourdomain.com"]'

# Production server configuration
export FS_API_SERVER__HOST=0.0.0.0
export FS_API_SERVER__PORT=8080
export FS_API_SERVER__WORKERS=4
```

### API Authentication (`api_auth`)

Controls authentication for the API server endpoints.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `auth_type` | string\|null | `null` | Authentication method. Valid values: `"basic"`, `"bearer"`, or `null` to disable |
| `auth_token` | string\|null | `null` | Authentication token/credentials |

**Note:** Both `auth_type` and `auth_token` must be set together or both be `null`. The `"forward"` auth type is not supported for API authentication.

See [API Authentication](api-authentication.md) for detailed examples.

### Scanner (`scanner`)

Settings for the stockpile scanner.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `database_path` | string | `"database.pkl"` | Path to the template database file |
| `early_exit_threshold` | float | `0.0` | Early exit threshold for icon matching (0.0-1.0). Set to 0.0 to disable early exit |
| `faction_filter` | string\|null | `null` | Filter items by faction. Valid values: `"neutral"`, `"Colonials"`, `"Wardens"`, or `null` for all |
| `custom_model` | string | `"renner_numbers"` | Tesseract custom OCR model name |
| `tessdata_path` | string | `"./tessdata"` | Path to Tesseract data directory |
| `debug_mode` | boolean | `false` | Enable debug mode to save debug images |
| `screenshots_folder` | string | `""` | Folder to save screenshots before processing. Empty string disables saving. Screenshots are saved in daily subfolders with format: `Date_HourWithSeconds_StorageType_Name_Resolution.png` |
| `max_ncc_candidates` | integer | `25` | Maximum number of NCC candidates to consider for matching |
| `phash_threshold` | integer | `12` | Maximum Hamming distance for pHash filtering |

### Output Format (`output_format`)

Controls how scanner results are output.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `output_format` | string | `"json"` | Output format. Valid values: `"console"`, `"file"`, `"json"`, `"webhook"` |
| `file_path` | string | `"output.json"` | Path for file output (supports `{timestamp}` placeholder) |
| `webhook_url` | string\|null | `null` | Webhook URL for sending results |
| `webhook_auth_type` | string\|null | `null` | Webhook authentication. Valid values: `"basic"`, `"bearer"`, `"forward"`, or `null` |
| `webhook_token` | string\|null | `null` | Token for webhook authentication (required when auth_type is `"basic"` or `"bearer"`) |
| `webhook_client_auth_header` | string\|null | `null` | Header name to pass through from API client to webhook (required when auth_type is `"forward"`) |

See [Webhooks](webhooks.md) for webhook configuration details.

### Logging (`logging`)

Configure application logging behavior.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `log_level` | string | `"INFO"` | Global log level: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"` |
| `log_format` | string | `"[%(asctime)s] %(levelname)s..."` | Python logging format string |
| `date_format` | string | `"%Y-%m-%d %H:%M:%S"` | Date format for log messages |
| `rotate_logs` | boolean | `false` | Enable daily log rotation |
| `log_file` | string\|null | `null` | Path to log file, or `null` for console only |
| `loggers` | object | `{}` | Per-logger level overrides (e.g., `{"foxhole_stockpiles": "DEBUG"}`) |

### OCR (`ocr`)

Fine-tune OCR detection parameters (advanced users only).

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `height` | int | `2160` | Base resolution height for scaling |
| `box_width` | int | `84` | Width of quantity detection box |
| `box_height` | int | `64` | Height of quantity detection box |
| `column_offset` | int | `112` | Horizontal spacing between icons |
| `row_offset` | int | `78` | Vertical spacing between icons |
| `group_offset` | int | `98` | Vertical spacing for new groups |
| `title_margin` | int | `24` | Gap from icon to title |
| `title_min_width` | int | `600` | Minimum title width |
| `title_height` | int | `64` | Title height |
| `icon_to_quantity_offset` | int | `88` | Gap between icon and quantity |
| `gray_lower` | int | `15` | Lower bound for quantity box darkness |
| `gray_upper` | int | `98` | Upper bound for quantity box brightness |
| `pixel_diff_tolerance` | int | `2` | Pixel error tolerance |

**Note:** Only modify these if you understand the OCR detection algorithm. Incorrect values may reduce accuracy.

### Stockpile Types (`stockpile_types`)

Configure localized stockpile type names for different languages.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `encampment` | array[string] | `["Encampment", "Campement", ...]` | Localized names for Encampment stockpile type |
| `keep` | array[string] | `["Keep", "Place Forte", ...]` | Localized names for Keep stockpile type |
| `safe_house` | array[string] | `["Safe House", "Planque", ...]` | Localized names for Safe House stockpile type |
| `relic_base` | array[string] | `["Relic Base", "Base Relique", ...]` | Localized names for Relic Base stockpile type |
| `bunker_base` | array[string] | `["Bunker Base", "Base Bunker", ...]` | Localized names for Bunker Base stockpile type |
| `border_base` | array[string] | `["Border Base", "Base Frontalière", ...]` | Localized names for Border Base stockpile type |
| `town_base` | array[string] | `["Town Base", "Quartier Général", ...]` | Localized names for Town Base stockpile type |
| `bms_longhook` | array[string] | `["BMS - Longhook"]` | Localized names for BMS - Longhook stockpile type |
| `storage_depot` | array[string] | `["Storage Depot", "Dépôt", ...]` | Localized names for Storage Depot stockpile type |
| `seaport` | array[string] | `["Seaport", "Port", ...]` | Localized names for Seaport stockpile type |
| `undefined` | array[string] | `["Undefined"]` | Localized names for Undefined stockpile type |

**Note:** These settings define how stockpile types are recognized. The defaults include translations for different game languages (English, French, German, Portuguese, Russian, Chinese). You may need to modify these if:
- Tesseract OCR misreads stockpile names (e.g., "Bumker base" instead of "Bunker base")
- You want to add support for additional languages

When adding OCR misreads, include all default values plus the misread variation (e.g., for bunker_base, add "Bumker base" to the existing array).

### Templates (`templates`)

Configure crate color tint overlay generation.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `crate_blue_multiplier` | int | `145` | Blue channel multiplier (0-255) |
| `crate_blue_offset` | int | `82` | Blue channel offset (0-255) |
| `crate_green_multiplier` | int | `152` | Green channel multiplier (0-255) |
| `crate_green_offset` | int | `87` | Green channel offset (0-255) |
| `crate_red_multiplier` | int | `154` | Red channel multiplier (0-255) |
| `crate_red_offset` | int | `89` | Red channel offset (0-255) |

These settings control how crate overlays are applied during template generation.

## Common Configurations

### API Server with Bearer Authentication

```bash
export FS_API_AUTH__AUTH_TYPE=bearer
export FS_API_AUTH__AUTH_TOKEN=my-secret-token-123
```

### Scanner with Webhook Output

```bash
export FS_OUTPUT_FORMAT__OUTPUT_FORMAT=webhook
export FS_OUTPUT_FORMAT__WEBHOOK_URL=https://api.example.com/stockpiles
export FS_OUTPUT_FORMAT__WEBHOOK_AUTH_TYPE=bearer
export FS_OUTPUT_FORMAT__WEBHOOK_TOKEN=webhook-token-456
```

### Debug Mode with File Logging

```bash
export FS_LOGGING__LOG_LEVEL=DEBUG
export FS_LOGGING__LOG_FILE=/var/log/foxhole-scanner.log
export FS_SCANNER__DEBUG_MODE=true
```

### Save Screenshots for Analysis

```bash
# Save all processed screenshots to a folder
export FS_SCANNER__SCREENSHOTS_FOLDER=screenshots

# Screenshots will be organized in daily subfolders:
# screenshots/2025-10-05/2025-10-05_14-30-45_Storage_Depot_My_Logi_1920x1080.png
```

### Production API Server

```json
{
  "api_server": {
    "cors_allow_origins": ["https://myapp.com", "https://app.myapp.com"]
  },
  "api_auth": {
    "auth_type": "bearer",
    "auth_token": "production-token"
  },
  "logging": {
    "log_level": "INFO",
    "log_file": "/var/log/foxhole-api.log",
    "rotate_logs": true
  },
  "scanner": {
    "database_path": "/opt/foxhole/templates.pkl"
  },
  "output_format": {
    "output_format": "webhook",
    "webhook_url": "https://api.myapp.com/stockpiles",
    "webhook_auth_type": "bearer",
    "webhook_token": "internal-webhook-secret"
  }
}
```

## Configuration Priority

Settings are resolved in this order (highest to lowest priority):

1. Environment variables (`FS_*`)
2. Configuration file (`~/.fs_config`)
3. Default values

Environment variables always override configuration file settings.

## Complete Configuration Reference

### Full `.fs_config` Example

This example shows all available settings with their default values:

```json
{
  "api_server": {
    "cors_allow_origins": ["*"]
  },
  "api_auth": {
    "auth_type": null,
    "auth_token": null
  },
  "logging": {
    "loggers": {},
    "log_level": "INFO",
    "log_format": "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "rotate_logs": false,
    "log_file": null
  },
  "ocr": {
    "height": 2160,
    "box_width": 84,
    "box_height": 64,
    "column_offset": 112,
    "row_offset": 78,
    "group_offset": 98,
    "title_margin": 24,
    "title_min_width": 600,
    "title_height": 64,
    "icon_to_quantity_offset": 88,
    "gray_lower": 15,
    "gray_upper": 98,
    "pixel_diff_tolerance": 2
  },
  "output_format": {
    "output_format": "json",
    "file_path": "output.json",
    "webhook_auth_type": null,
    "webhook_token": null,
    "webhook_url": null,
    "webhook_client_auth_header": null
  },
  "scanner": {
    "database_path": "database.pkl",
    "early_exit_threshold": 0.0,
    "faction_filter": null,
    "custom_model": "renner_numbers",
    "tessdata_path": "./tessdata",
    "debug_mode": false,
    "screenshots_folder": "",
    "max_ncc_candidates": 25,
    "phash_threshold": 12
  },
  "stockpile_types": {
    "encampment": ["Encampment", "Campement", "Feldlager", "Acampamento", "Лагерь", "营地"],
    "keep": ["Keep", "Place Forte", "Wehrturm", "Torreão", "Крепость", "要塞"],
    "safe_house": ["Safe House", "Planque", "Unterschlupf", "Casa Fortificada", "Yбeжищe", "安全屋"],
    "relic_base": ["Relic Base", "Base Relique", "Reliktbasis", "Base Relíquia", "Peликтoвая база", "遗迹基地"],
    "bunker_base": ["Bunker Base", "Base Bunker", "Bunkerbasis", "Centro do Bunker", "Base de Bunker", "Base de Casamata", "Бункерная база", "Бункерная База", "地堡基地"],
    "border_base": ["Border Base", "Base Frontalière", "Grenzbasis", "Base Fronteiriça", "Пограничная База", "边境基地"],
    "town_base": ["Town Base", "Quartier Général", "Stadtkernbasis", "Base de Cidade", "Ратуша", "城镇基地"],
    "bms_longhook": ["BMS - Longhook"],
    "storage_depot": ["Storage Depot", "Dépôt", "Lagerdepot", "Depósito", "Складское Помещение", "仓库"],
    "seaport": ["Seaport", "Port", "Seehafen", "Porto", "Морской порт", "海港"],
    "undefined": ["Undefined"]
  },
  "templates": {
    "crate_blue_multiplier": 145,
    "crate_blue_offset": 82,
    "crate_green_multiplier": 152,
    "crate_green_offset": 87,
    "crate_red_multiplier": 154,
    "crate_red_offset": 89
  }
}
```

### All Environment Variables

This table lists all available environment variables with their default values:

| Environment Variable | Type | Default Value | Description |
|---------------------|------|---------------|-------------|
| **API Server** | | | |
| `FS_API_SERVER__CORS_ALLOW_ORIGINS` | JSON array | `["*"]` | CORS allowed origins |
| `FS_API_SERVER__HOST` | string | `"127.0.0.1"` | Server bind host |
| `FS_API_SERVER__PORT` | integer | `8000` | Server bind port |
| `FS_API_SERVER__WORKERS` | integer | `1` | Number of worker processes |
| `FS_API_SERVER__RELOAD` | boolean | `false` | Enable auto-reload |
| `FS_API_SERVER__LOG_LEVEL` | string | `"info"` | Server log level (`"debug"`, `"info"`, `"warning"`, `"error"`) |
| **API Authentication** | | | |
| `FS_API_AUTH__AUTH_TYPE` | string\|null | `null` | API auth type (`"basic"`, `"bearer"`, or `null`) |
| `FS_API_AUTH__AUTH_TOKEN` | string\|null | `null` | API authentication token |
| **Logging** | | | |
| `FS_LOGGING__LOGGERS` | JSON object | `{}` | Per-logger level overrides (see special syntax below) |
| `FS_LOGGING__LOGGERS__<LOGGER_NAME>` | string | N/A | Logger-specific level (e.g., `__foxhole_stockpiles`, `__uvicorn`) |
| `FS_LOGGING__LOG_LEVEL` | string | `"INFO"` | Global log level |
| `FS_LOGGING__LOG_FORMAT` | string | `"[%(asctime)s] %(levelname)s [%(name)s] %(message)s"` | Log format string |
| `FS_LOGGING__DATE_FORMAT` | string | `"%Y-%m-%d %H:%M:%S"` | Date format |
| `FS_LOGGING__ROTATE_LOGS` | boolean | `false` | Enable log rotation |
| `FS_LOGGING__LOG_FILE` | string\|null | `null` | Log file path |
| **OCR Detection** | | | |
| `FS_OCR__HEIGHT` | integer | `2160` | Base height for scaling |
| `FS_OCR__BOX_WIDTH` | integer | `84` | Quantity box width |
| `FS_OCR__BOX_HEIGHT` | integer | `64` | Quantity box height |
| `FS_OCR__COLUMN_OFFSET` | integer | `112` | Horizontal icon spacing |
| `FS_OCR__ROW_OFFSET` | integer | `78` | Vertical icon spacing |
| `FS_OCR__GROUP_OFFSET` | integer | `98` | Group vertical spacing |
| `FS_OCR__TITLE_MARGIN` | integer | `24` | Gap to title |
| `FS_OCR__TITLE_MIN_WIDTH` | integer | `600` | Minimum title width |
| `FS_OCR__TITLE_HEIGHT` | integer | `64` | Title height |
| `FS_OCR__ICON_TO_QUANTITY_OFFSET` | integer | `88` | Icon to quantity gap |
| `FS_OCR__GRAY_LOWER` | integer | `15` | Quantity box dark threshold |
| `FS_OCR__GRAY_UPPER` | integer | `98` | Quantity box bright threshold |
| `FS_OCR__PIXEL_DIFF_TOLERANCE` | integer | `2` | Pixel error tolerance |
| **Output Format** | | | |
| `FS_OUTPUT_FORMAT__OUTPUT_FORMAT` | string | `"json"` | Output format (`"console"`, `"file"`, `"json"`, `"webhook"`) |
| `FS_OUTPUT_FORMAT__FILE_PATH` | string | `"output.json"` | File output path |
| `FS_OUTPUT_FORMAT__WEBHOOK_AUTH_TYPE` | string\|null | `null` | Webhook auth type (`"basic"`, `"bearer"`, `"forward"`, or `null`) |
| `FS_OUTPUT_FORMAT__WEBHOOK_TOKEN` | string\|null | `null` | Webhook auth token |
| `FS_OUTPUT_FORMAT__WEBHOOK_URL` | string\|null | `null` | Webhook URL |
| `FS_OUTPUT_FORMAT__WEBHOOK_CLIENT_AUTH_HEADER` | string\|null | `null` | Client auth header to pass through |
| **Scanner** | | | |
| `FS_SCANNER__DATABASE_PATH` | string | `"database.pkl"` | Template database path |
| `FS_SCANNER__EARLY_EXIT_THRESHOLD` | float | `0.0` | Early exit threshold |
| `FS_SCANNER__FACTION_FILTER` | string\|null | `null` | Faction filter (`"neutral"`, `"Colonials"`, `"Wardens"`, or `null`) |
| `FS_SCANNER__CUSTOM_MODEL` | string | `"renner_numbers"` | Tesseract custom model name |
| `FS_SCANNER__TESSDATA_PATH` | string | `"./tessdata"` | Tesseract data directory |
| `FS_SCANNER__DEBUG_MODE` | boolean | `false` | Enable debug image output |
| `FS_SCANNER__SCREENSHOTS_FOLDER` | string | `""` | Folder to save screenshots (empty to disable) |
| `FS_SCANNER__MAX_NCC_CANDIDATES` | integer | `25` | Max NCC candidates |
| `FS_SCANNER__PHASH_THRESHOLD` | integer | `12` | pHash Hamming distance threshold |
| **Templates** | | | |
| `FS_TEMPLATES__CRATE_BLUE_MULTIPLIER` | integer | `145` | Crate blue channel multiplier |
| `FS_TEMPLATES__CRATE_BLUE_OFFSET` | integer | `82` | Crate blue channel offset |
| `FS_TEMPLATES__CRATE_GREEN_MULTIPLIER` | integer | `152` | Crate green channel multiplier |
| `FS_TEMPLATES__CRATE_GREEN_OFFSET` | integer | `87` | Crate green channel offset |
| `FS_TEMPLATES__CRATE_RED_MULTIPLIER` | integer | `154` | Crate red channel multiplier |
| `FS_TEMPLATES__CRATE_RED_OFFSET` | integer | `89` | Crate red channel offset |

**Note:** For JSON values (arrays/objects), use proper JSON syntax in the environment variable:
```bash
export FS_API_SERVER__CORS_ALLOW_ORIGINS='["https://example.com"]'
```

#### Per-Logger Level Configuration

The `loggers` setting has special syntax for environment variables. You can set logger-specific levels in two ways:

**Method 1: Individual logger variables (recommended)**
```bash
export FS_LOGGING__LOGGERS__foxhole_stockpiles=DEBUG
export FS_LOGGING__LOGGERS__uvicorn=WARNING
export FS_LOGGING__LOGGERS__httpx=ERROR
```

**Method 2: JSON object**
```bash
export FS_LOGGING__LOGGERS='{"foxhole_stockpiles":"DEBUG","uvicorn":"WARNING"}'
```

**In config file:**
```json
{
  "logging": {
    "loggers": {
      "foxhole_stockpiles": "DEBUG",
      "uvicorn": "WARNING",
      "httpx": "ERROR"
    }
  }
}
```

Valid log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

When a logger-specific level is set, it overrides the global `log_level` for that logger only.
