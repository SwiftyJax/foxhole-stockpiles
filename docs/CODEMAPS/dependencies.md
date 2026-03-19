# External Dependencies & Tools

**Last Updated:** 2026-03-19

## Runtime Dependencies

### Python Packages

```toml
# Image Processing & Computer Vision
opencv-python-headless>=4.13.0.90    # Image processing, template matching, NCC
numpy>=2.4.2                         # Numerical operations, arrays
pillow>=12.1.1                       # Image I/O, PIL compatibility

# OCR & Text Recognition
pytesseract>=0.3.13                  # Tesseract OCR wrapper
# Requires: Tesseract binary (external)
#   - Windows: https://github.com/UB-Mannheim/tesseract/wiki
#   - Linux: sudo apt install tesseract-ocr
#   - macOS: brew install tesseract

# Data Serialization & Validation
pydantic>=2.12.3                     # Data validation, settings
pydantic_settings>=2.13.1            # Environment variable integration
h5py>=3.11.0                         # HDF5 database access

# Web Framework
fastapi>=0.129.2                     # REST API framework
uvicorn[standard]>=0.41.0            # ASGI server
python-multipart>=0.0.22             # Multipart form handling
jinja2>=3.1.0                        # HTML templating
slowapi>=0.1.9                       # Rate limiting

# Desktop UI
PyQt6>=6.10.2                        # GUI application framework

# Networking & Webhooks
httpx>=0.28.1                        # Async HTTP client
discord-webhook>=1.3.1               # Discord integration

# System Monitoring
psutil>=7.2.2                        # Process/system utilities
memory-profiler>=0.61.0              # Memory profiling

# HTTP/Requests
requests (via discord-webhook)       # HTTP requests
```

**Total Dependencies:** ~15 core packages + transitive dependencies

### External Binaries

#### 1. Tesseract OCR (Required)
**Purpose:** Text recognition from quantity box images
**Version:** 5.x+ recommended
**Status:** Required - fails at startup if not found

**Installation:**
```bash
# Windows (via installer)
# https://github.com/UB-Mannheim/tesseract/wiki

# Linux (apt)
sudo apt install tesseract-ocr

# macOS (brew)
brew install tesseract

# Verify installation
tesseract --version
```

**Custom Model:**
- Location: `/tessdata/renner_numbers.traineddata`
- Training data for number recognition
- Used when `scanner.custom_model=true` (default)

#### 2. repak (Optional)
**Purpose:** Extract game assets from PAK files
**Status:** Required only for `fs extract-assets` command
**Platform:** Windows binary

**Integration:** `/foxhole_stockpiles/connectors/repak.py`

```python
def extract_pak(
    pak_path: Path,
    output_dir: Path,
    repak_path: Path | None = None
) -> None:
    """Extract PAK file using repak binary."""
    # Detects Windows/Linux paths automatically
```

**Configuration:**
```python
class ExternalToolsSettings(BaseSettings):
    repak_path: Path | None = None
    umodel_path: Path | None = None
```

**Environment Variable:**
```bash
FS_EXTERNAL_TOOLS__REPAK_PATH=/path/to/repak.exe
```

#### 3. umodel (Optional)
**Purpose:** Convert Unreal Engine assets to accessible formats
**Status:** Required only for asset extraction pipeline
**Platform:** Windows executable

**Integration:** `/foxhole_stockpiles/connectors/umodel.py`

## Dependency Resolution Map

```
                         fastapi>=0.129.2
                               ↓
                    ┌──────────┴──────────┐
                    ↓                     ↓
              starlette             pydantic>=2.12.3
                    ↓                     ↓
              uvicorn[standard]    pydantic_settings>=2.13.1
                    ↓                     ↓
           hypercorn/httptools       typing_extensions

            slowapi>=0.1.9
                    ↓
              limits (rate limiting)

            opencv-python-headless>=4.13.0.90
                    ↓
              numpy>=2.4.2

            pytesseract>=0.3.13
                    ↓
              [External: Tesseract binary]

            h5py>=3.11.0
                    ↓
              numpy>=2.4.2

            PyQt6>=6.10.2
                    ↓
              PyQt6-sip, PyQt6-Qt6

            httpx>=0.28.1
                    ↓
              h11, sniffio, anyio

            discord-webhook>=1.3.1
                    ↓
              requests, httplib2
```

## Version Compatibility

### Python Version
- **Required:** 3.12+
- **Tested:** 3.12, 3.13
- **Not Supported:** < 3.12 (uses `dict[str, Any]` syntax)

### Operating Systems
- **Linux:** Full support
- **Windows:** Full support (with Tesseract)
- **macOS:** Full support (with Tesseract)
- **WSL2:** Supported (special path handling for Windows tools)

### Special Cases

#### WSL2 Interoperability
When running Python on WSL2 with Windows-compiled tools:

```python
# Path conversion: WSL → Windows format
wsl_path = "/mnt/c/Users/name/tools/repak.exe"
# Converts to: "C:\\Users\\name\\tools\\repak.exe"

# Used in: /foxhole_stockpiles/connectors/
```

## Development Dependencies

```toml
[project.optional-dependencies]
dev = [
    # Testing
    "pytest>=9.0.2"                    # Test framework
    "pytest-asyncio>=1.2.0"            # Async test support
    "pytest-cov>=7.0.0"                # Coverage measurement
    "pytest-xdist>=3.5.0"              # Parallel test execution
    "pytest-qt>=4.5.0"                 # PyQt6 testing

    # Code Quality
    "mypy>=1.19.1"                     # Static type checking (strict mode)
    "ruff>=0.15.2"                     # Linter + formatter
    "pre-commit>=4.5.1"                # Pre-commit hooks

    # Type Stubs
    "types-requests"
    "types-psutil"
    "h5py-stubs"
]
```

## Configuration File Examples

### ~/.fs_config (JSON)
```json
{
  "config_version": 5,
  "scanner": {
    "database_path": "/home/user/.stockpiles/templates.h5",
    "tessdata_path": "./tessdata",
    "custom_model": true,
    "template_cache_size": 1000,
    "min_confidence": 0.75,
    "max_phash_distance": 10
  },
  "api_server": {
    "host": "0.0.0.0",
    "port": 8000,
    "workers": 4,
    "enable_memory_monitoring": false,
    "auto_trim_memory": false
  },
  "notifications": {
    "enabled": false,
    "discord": {
      "webhook_url": "https://discord.com/api/webhooks/..."
    }
  }
}
```

### Environment Variables
```bash
# Scanner
FS_SCANNER__DATABASE_PATH=/path/to/db.h5
FS_SCANNER__CUSTOM_MODEL=true

# API Server
FS_API_SERVER__HOST=0.0.0.0
FS_API_SERVER__PORT=8000
FS_API_SERVER__WORKERS=4

# Authentication
FS_API_AUTH__AUTH_TYPE=bearer
FS_API_AUTH__BEARER_TOKEN=my-secret-token

# External Tools
FS_EXTERNAL_TOOLS__REPAK_PATH=/path/to/repak.exe
FS_EXTERNAL_TOOLS__UMODEL_PATH=/path/to/umodel.exe

# Notifications
FS_NOTIFICATIONS__ENABLED=true
FS_NOTIFICATIONS__DISCORD__WEBHOOK_URL=https://...
```

## Performance Characteristics

### Memory Usage
- **Baseline:** ~150-200 MB (services loaded)
- **Per Scan:** ~50-100 MB (depending on image size)
- **Template Cache:** ~500 MB-1 GB (1000 templates at 1920px)
- **Peak (with GC disabled):** 1-2 GB

### Processing Times
- **Image Loading:** 10-30 ms
- **Detection:** 50-150 ms
- **Template Matching:** 100-300 ms
- **OCR:** 500-1500 ms (Tesseract)
- **Total:** 700-2000 ms per scan

### Database Performance
- **Load Time:** 1-3 seconds (first request)
- **Template Lookup:** O(1) by faction/mod
- **pHash Filter:** ~1 ms (5000 templates)
- **NCC Scoring:** 50-200 ms per match (vectorized)

## Networking

### HTTP Client
- **Library:** httpx (async)
- **Timeout:** 30 seconds (configurable)
- **Retries:** None (application level)
- **SSL Verification:** True (default)

### Discord Webhook
- **Library:** discord-webhook
- **Timeout:** 10 seconds
- **Retry Policy:** 3 retries on failure
- **Rate Limit:** None (Discord handles it)

## Security Dependencies

### Input Validation
- **Library:** Pydantic v2 (strict mode)
- **Validation Points:**
  - Image upload (size, format)
  - Configuration (types, ranges)
  - API parameters (enums, patterns)

### Authentication
- **No External Library** - Custom implementation
- **Methods:** Bearer token, API key, none
- **Storage:** Environment variables or config file (not hardcoded)

### CORS
- **Library:** FastAPI CORS middleware
- **Default:** Allow all origins (configurable)
- **Methods:** GET, POST, OPTIONS, etc.

## License Compatibility

```
Project: MIT License (https://github.com/xurxogr/foxhole-stockpiles)

Dependencies (All Compatible):
- numpy: BSD
- opencv-python: Apache 2.0
- fastapi: MIT
- pydantic: MIT
- h5py: BSD
- pytesseract: GPLv3 (compatible with MIT)
- PyQt6: GPLv3 (separate GUI module)
- discord-webhook: MIT
- All others: MIT/Apache/BSD
```

## Troubleshooting

### Tesseract Not Found
```
Error: Tesseract OCR not found
Solution: Install tesseract-ocr via system package manager
```

### OpenCV Headless Installation
```
Error: libGL.so.1 missing
Solution: Use opencv-python-headless (included by default)
```

### h5py on Windows
```
Error: Microsoft Visual C++ not installed
Solution: Pre-built wheels available, pip install should work
```

### PyQt6 Display Issues
```
Error: Qt platform plugin not found
Solution: QT_QPA_PLATFORM_PLUGIN_PATH environment variable
```

## Dependency Update Strategy

**Frequency:** Monthly security updates review
**Policy:** Pin major versions, allow minor/patch updates
**Testing:** Full test suite on dependency upgrades
**Breaking Changes:** Major version bumps require code review

## Key Files

1. `/pyproject.toml` - Dependency declarations
2. `/foxhole_stockpiles/core/logging.py` - Logging setup (uses logging module)
3. `/foxhole_stockpiles/connectors/` - External tool integration
4. `/foxhole_stockpiles/core/settings/` - Configuration management
