<!-- Generated: 2026-06-06 | Branch: refactor/01-pyside6 | Token estimate: ~850 -->

# Backend, API & CLI

## CLI `fs` (Typer)

**Entry:** `cli/app.py:main`. Settings loaded via `cli/_settings.py:get_app_settings`
(honours `--config <path>`), Rich output via `cli/_console.py`.

| Command | Module | Flow |
|---|---|---|
| `fs scan` | `cli/commands/scan.py` | `ScannerSettings` → `fs_ocr._impl.coordinator.OCRCoordinator` → `OutputCoordinator` |
| `fs serve` | `cli/commands/serve.py` | launches uvicorn on `api.server:app` |
| `fs gui` | `cli/commands/gui.py` | launches PySide6 desktop app |
| `fs sav` | `cli/commands/sav.py` | `SaveFileProcessor` (resolves `.sav` + map data) → `OutputCoordinator` |

> Asset/DB tooling commands (build-db, gen-templates, catalog, add-mod/icon,
> inspect, extract-assets) moved to the separate `fs-tools` CLI.

## FastAPI server (`api/server.py`)

```python
app = FastAPI(title="Foxhole Stockpile Scanner API", version="0.4.0")
limiter = Limiter(key_func=get_remote_address)   # slowapi
```

**Lifespan:** startup verifies Tesseract, loads config, checks DB; shutdown
emits notifications + cleanup.

### Routes

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | no | health/version (`HealthResponse`) |
| POST | `/ocr/scan_image` | yes | main OCR; rate-limited; `multipart` image + `faction`/`language`/`mods` query → `ScanResult` |
| GET | `/memory/stats` | yes | memory snapshot stats |
| POST | `/memory/gc` | yes | force GC |
| GET | `/memory/current` | yes | current memory |
| GET | `/memory/gc-stats` | yes | GC stats |
| GET | `/scan/stats` | yes | scan counters |

**Web UI** (`api/web/routes.py`, `APIRouter`, auth-gated):

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Jinja upload form (`templates/`) |
| POST | `/web/scan` | form submit → HTML results |
| GET | `/web/icon/{code}` | serve item icon image |

### scan_image handler shape

```python
@app.post("/ocr/scan_image", dependencies=[Depends(auth_dependency)])
@limiter.limit(...)   # configured rate
async def scan_image(request, image: UploadFile,
                     coordinator = Depends(get_ocr_coordinator),
                     output_coordinator = Depends(get_output_coordinator),
                     faction: ItemFaction | None = Query(None),
                     language: SupportedLanguage | None = Query(None)) -> Any
```

## Auth (`api/auth.py`)

Factory builds a dependency from `APIAuthSettings.auth_type`:
- `NONE` → no-op
- `BEARER` → `HTTPBearer`, compares `bearer_token`
- `API_KEY` → `X-API-Key` header, compares `api_key`

Env: `FS_API_AUTH__AUTH_TYPE=bearer`, `FS_API_AUTH__BEARER_TOKEN=...`.

## Dependency injection (`api/dependencies.py`)

`get_settings`, `get_ocr_coordinator`, `get_output_coordinator`,
`get_catalog_service`, `get_notification_service` — cached per process/request.

## Middleware (`api/`)

1. **CORS** — origins from `api_server.cors_allow_origins`.
2. **Security headers** — CSP, `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy` on HTML.
3. **MemoryMonitorMiddleware** (`memory_middleware.py`) — optional per-request memory tracking + auto-trim, gated by `api_server.enable_memory_monitoring`.

## Rate limiting (`api/scan_limiter.py`)

slowapi `Limiter` keyed by remote address; exceed → 429. Limit value sourced
from settings (default ~30/min on `/ocr/scan_image`).

## Output routing (`services/output_coordinator.py`)

```python
async def handle_output(stockpile) -> dict | None:
    for cfg in output_settings.handlers:
        result = await make_handler(cfg).handle(stockpile, format=cfg.format)
        if result is not None:
            return result   # first non-None (e.g. ReturnHandler for API) wins
```

Handlers (`handlers/`): `console.py`, `file.py` (JSON/CSV/TSV), `webhook.py`
(HTTP POST), `response.py` (API return). Interface: `base_handler.py`.

## Response models

- `ScanResult` — `{success, data: Stockpile|None, error, processing_time_ms}`.
- `Stockpile` / `StockpileItem` — see data.md.

## API server config (`core/settings/sections/api.py`)

`APIServerSettings`: `host`, `port`, `workers`, `reload`, `log_level`,
`enable_memory_monitoring`, `auto_trim_memory`, `memory_trim_threshold`,
`cors_allow_origins`, `max_upload_size_bytes`.

```bash
fs serve                       # via CLI
FS_API_SERVER__PORT=8000       # env override
```

## Key files

1. `cli/app.py` — CLI root
2. `cli/commands/scan.py` — scan wiring
3. `api/server.py` — routes + middleware
4. `api/auth.py` — auth dependency factory
5. `services/output_coordinator.py` — sink fan-out
