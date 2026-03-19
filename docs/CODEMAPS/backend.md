# Backend & API Routes

**Last Updated:** 2026-03-19

## FastAPI Server Configuration

**File:** `/foxhole_stockpiles/api/server.py`

```python
# Main application
app = FastAPI(
    title="Foxhole Stockpile Scanner API",
    description="API for analyzing Foxhole stockpile screenshots",
    version="0.4.0"
)

# Middleware stack
- CORSMiddleware (configurable origins)
- MemoryMonitorMiddleware (optional memory tracking)
- SecurityHeadersMiddleware (CSP, X-Frame-Options, etc.)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Global services
app_settings: AppSettings  # Configuration singleton
memory_monitor: MemoryMonitor  # Memory tracking
```

**Lifespan Events:**
- Startup: Verify Tesseract, load config, check database
- Shutdown: Send notifications, cleanup resources

## API Endpoints

### 1. Health Check
```
GET /health
Response: HealthResponse
  {
    "status": "healthy",
    "version": "0.4.0"
  }
Status: 200 OK
```

**Purpose:** Load balancer health check, service availability verification

### 2. Main OCR Endpoint
```
POST /ocr/scan_image
Content-Type: multipart/form-data

Parameters:
  - image (UploadFile): Screenshot image (PNG/JPG, max 10MB)
  - faction (ItemFaction | null): Filter by Colonial/Warden
  - language (SupportedLanguage | null): OCR language (en, pt, fr, de, ru, zh)
  - mods (list[str] | null): Specific mods to search

Authentication: Required (Bearer token or API key)
Rate Limit: 30 requests per minute
Timeout: 60 seconds

Response: ScanResult
  {
    "success": true,
    "data": Stockpile,
    "error": null,
    "processing_time_ms": 245.5
  }

Status Codes:
  - 200 OK: Scan completed successfully
  - 400 Bad Request: Invalid image format/size
  - 401 Unauthorized: Missing/invalid credentials
  - 429 Too Many Requests: Rate limit exceeded
  - 503 Service Unavailable: Tesseract/database error
```

**File:** `/foxhole_stockpiles/api/server.py:233-290`

**Handler Function:**
```python
@app.post("/ocr/scan_image", dependencies=[Depends(auth_dependency)])
@limiter.limit("30/minute")
async def scan_stockpile(
    request: Request,
    image: UploadFile,
    coordinator: Annotated[OCRCoordinator, Depends(get_ocr_coordinator)],
    output_coordinator: Annotated[OutputCoordinator, Depends(get_output_coordinator)],
    faction: Annotated[ItemFaction | None, Query()] = None,
    language: Annotated[SupportedLanguage | None, Query()] = None,
) -> Any:
    """Scan a stockpile screenshot and return detected items."""
```

### 3. Web Interface Routes

**File:** `/foxhole_stockpiles/api/web/routes.py`

```
GET / → HTMLResponse
  Renders: templates/index.html
  Context: version, db_error
  Purpose: Web UI for image upload

POST /web/scan → HTMLResponse
  Form: images (list), action (scan|send)
  Response: HTML results table
  Purpose: Submit images via web form

GET /web/icons/{mod_name}/{code}.png → StreamingResponse
  Purpose: Retrieve item icon images
  Cache: In-memory with size limit

GET /web/api/mods → JSONResponse
  Response: {"mods": ["vanilla", "airborne", ...]}
  Purpose: List available mods for UI dropdown

GET /web/api/categories → JSONResponse
  Response: {"categories": ["Weapons", "Ammo", ...]}
  Purpose: List item categories for filtering
```

## Web Router Configuration

**File:** `/foxhole_stockpiles/api/web/routes.py:31-44`

```python
router = APIRouter(
    tags=["web"],
    dependencies=[Depends(auth_dependency)]
)

# Templates
templates = Jinja2Templates(directory=str(templates_dir))
```

## Authentication System

**File:** `/foxhole_stockpiles/api/auth.py`

```python
def create_auth_dependency(settings: APIAuthSettings) -> Callable:
    """Create authentication dependency based on configured auth type."""

    if settings.auth_type == AuthType.NONE:
        return lambda: None
    elif settings.auth_type == AuthType.BEARER:
        return HTTPBearer(auto_error=True)
    elif settings.auth_type == AuthType.API_KEY:
        return APIKeyHeader(name="X-API-Key", auto_error=True)
```

**Configuration:**
```python
class APIAuthSettings(BaseSettings):
    auth_type: AuthType = AuthType.NONE
    bearer_token: str | None = None
    api_key: str | None = None
```

**Environment Variables:**
```bash
FS_API_AUTH__AUTH_TYPE=bearer
FS_API_AUTH__BEARER_TOKEN=my-secret-token
```

## Dependency Injection

**File:** `/foxhole_stockpiles/api/dependencies.py`

```python
def get_settings() -> AppSettings:
    """Return cached application settings."""
    return app_settings

def get_ocr_coordinator() -> OCRCoordinator:
    """Create and cache OCR coordinator."""
    # Lazy initialization, cached per request

def get_output_coordinator() -> OutputCoordinator:
    """Create output coordinator for handling results."""

def get_catalog_service() -> CatalogService:
    """Load catalog for item metadata lookup."""

def get_icon_service() -> IconService:
    """Create icon service for image retrieval."""

def get_notification_service() -> NotificationService:
    """Create notification service for webhooks."""
```

**Pattern:** FastAPI dependency injection with caching

## Middleware Stack

### 1. CORS Middleware
```python
CORSMiddleware(
    allow_origins=app_settings.api_server.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

### 2. Security Headers Middleware
```python
# Adds to HTML responses:
Content-Security-Policy: default-src 'self'; img-src 'self' data:; ...
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
```

### 3. Memory Monitor Middleware
```python
class MemoryMonitorMiddleware:
    """Optional memory tracking for each request."""
    - Snapshot memory before request
    - Capture peak memory during processing
    - Log warnings if threshold exceeded
    - Optional: Force GC if memory > limit
```

**Configuration:**
```python
if app_settings.api_server.enable_memory_monitoring:
    app.add_middleware(MemoryMonitorMiddleware, ...)
```

## Request/Response Models

### ScanResult (API Response Envelope)
```python
class ScanResult(BaseModel):
    success: bool
    data: Stockpile | None = None
    error: str | None = None
    processing_time_ms: float

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": true,
            "data": {...},
            "error": null,
            "processing_time_ms": 245.5
        }
    })
```

### Stockpile (Main Output Model)
**File:** `/foxhole_stockpiles/models/stockpile.py`

```python
class Stockpile(BaseModel):
    name: str                          # Stockpile name (e.g., "Logi")
    type: StockpileType                # Type enum
    items: list[StockpileItem]         # Detected items
    timestamp: datetime                # Processing time
    shard: str                         # Server shard (e.g., "ABLE")
    ingame_timestamp: str              # In-game time (e.g., "Day 1293, 19:06")
    resolution: str | None             # Screenshot resolution
    errors: list[str]                  # Processing errors/warnings
```

### StockpileItem (Individual Item)
**File:** `/foxhole_stockpiles/models/stockpile_item.py`

```python
class StockpileItem(BaseModel):
    code: str                          # Item code (e.g., "8MASS")
    quantity: str                      # Extracted quantity (e.g., "450")
    confidence: float                  # Template match confidence (0-1)
    faction: ItemFaction | None        # Colonial/Warden
    category: ItemCategory | None      # Item category
    crated: bool                       # Crate overlay detected
    resolution: SupportedResolution    # Template resolution used
```

## Error Handling

### HTTP Status Codes
```
200 OK
  ├─ Success: Stockpile processed
  └─ Partial success: Some items with errors

400 Bad Request
  ├─ Invalid image format
  ├─ File too large (>10MB)
  └─ Missing required parameters

401 Unauthorized
  └─ Invalid/missing authentication token

429 Too Many Requests
  └─ Rate limit exceeded (30/min)

503 Service Unavailable
  ├─ Tesseract OCR not found
  ├─ Database not accessible
  └─ Configuration error
```

### Error Response
```json
{
  "success": false,
  "data": null,
  "error": "Tesseract OCR not found. Install tesseract-ocr.",
  "processing_time_ms": 15.2
}
```

## Rate Limiting

**File:** `/foxhole_stockpiles/api/server.py:47, 234`

```python
limiter = Limiter(key_func=get_remote_address)

@limiter.limit("30/minute")
async def scan_stockpile(...) -> Any:
    """Rate limited to 30 requests per minute per IP."""
```

**Handler:**
```python
def rate_limit_exceeded_handler(request: Request, _exc: Exception) -> Response:
    return Response(
        content='{"detail": "Rate limit exceeded"}',
        status_code=429,
        media_type="application/json"
    )
```

## Logging Configuration

**File:** `/foxhole_stockpiles/core/logging.py`

**Startup:**
```python
logger = logging.getLogger(__name__)
logger.info("Starting Foxhole Stockpile Scanner API v%s", get_version_info())
logger.info("Database path: %s", app_settings.scanner.database_path)
logger.info("Available mods in database: %s", ", ".join(mods_list))
logger.info("Tesseract OCR version: %s", version)
```

**Request Logging:**
```
INFO: Scan started - resolution: 1920x1080
INFO: Detected 24 items in stockpile
INFO: Processing time: 245.5ms
```

## Configuration for API Server

**File:** `/foxhole_stockpiles/core/settings/sections/api.py`

```python
class APIServerSettings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False  # Dev only
    workers: int = 1
    log_level: str = "info"
    enable_memory_monitoring: bool = False
    auto_trim_memory: bool = False
    memory_trim_threshold: int = 512  # MB
    cors_allow_origins: list[str] = ["*"]
    max_upload_size_bytes: int = 10485760  # 10MB
```

**Usage:**
```python
# Environment
FS_API_SERVER__HOST=0.0.0.0
FS_API_SERVER__PORT=8000
FS_API_SERVER__WORKERS=4

# Config file (~/.fs_config)
{
  "api_server": {
    "host": "0.0.0.0",
    "port": 8000,
    "workers": 4
  }
}
```

## Command to Start Server

```bash
fs server
# or directly:
python -m foxhole_stockpiles.commands.api_server.api_server
# or with uvicorn:
uvicorn foxhole_stockpiles.api.server:app --host 0.0.0.0 --port 8000 --workers 4
```

## Key Service Files

1. `/foxhole_stockpiles/api/server.py` - FastAPI app, routes, middleware
2. `/foxhole_stockpiles/api/dependencies.py` - Dependency injection
3. `/foxhole_stockpiles/api/auth.py` - Authentication logic
4. `/foxhole_stockpiles/api/web/routes.py` - Web UI endpoints
5. `/foxhole_stockpiles/core/settings/sections/api.py` - API configuration
