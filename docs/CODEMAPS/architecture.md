<!-- Generated: 2026-06-06 | Branch: refactor/01-pyside6 | Token estimate: ~900 -->

# Architecture & Design Patterns

**Type:** multi-package Python workspace (flat layout), 3 installable packages.
Config schema **v8**.

## Package boundaries

```
foxhole_stockpiles ──depends──> fs_ocr ──reuses──> foxhole_stockpiles.models
        │                          │
        └── fs_tools (independent app: builds the data fs_ocr consumes)
```

- **foxhole_stockpiles** — user-facing runtime: CLI, REST API, web UI, GUI, SAV.
- **fs_ocr** — OCR engine as a standalone package. Public API in `fs_ocr/api.py`;
  pure-Python impl in `fs_ocr/_impl/`. Re-exports `Stockpile`/`StockpileItem`
  from the runtime so output models match. Being aligned to a Rust replacement
  (`../fs-ocr`); `ScannerInfo.implementation` reports `"python"`/`"rust"`.
- **fs_tools** — build-time tooling (catalog, template DB, asset extraction).
  Self-contained: own `core/settings`, `models`, `gui`, `i18n`.

## Design philosophy

1. **Service layer** — focused single-responsibility classes, constructor injection.
2. **Pluggable OCR backend** — `OCRScanner` API hides `_impl`; schema-versioned seam for a Rust swap.
3. **Multi-handler output** — one result fans out to console/file/webhook/response.
4. **Event-driven notifications** — decoupled via `EventBus` (`core/events/bus.py`).
5. **Config as code** — Pydantic settings, env overrides, versioned migration.

## OCR scan pipeline (screenshot → structured data)

Orchestrator: `fs_ocr/_impl/coordinator.py` → `OCRCoordinator.scan_stockpile()`.

```
image (NDArray)
  │
  ▼ _impl/detector.py  (StockpileDetector)
    scale by resolution (1920px base) → detect icon boxes, quantity boxes, groups
  │
  ▼ _impl/classifier.py  (StockpileTypeClassifier)
    text-pattern match → StockpileType
  │
  ▼ _impl/template_manager.py + template_database.py
    Phase 1 pHash prefilter (O(1) faction/mod/category sets)
    Phase 2 NCC scoring on survivors
    Phase 3 tiebreaker: mean pixel diff when NCC within ~0.0015
    → conflict resolution (dedupe across groups, confidence ranking)
  │
  ▼ _impl/extractor.py  (StockpileTextExtractor)
    Otsu threshold → morphology → Tesseract (renner_numbers) → regex digits
  │
  ▼ Stockpile model
  │
  ▼ services/output_coordinator.py → handlers/* (first non-None result wins)
```

Public entry: `fs_ocr.api.OCRScanner(ScannerConfig).scan()/scan_sync()`.

## SAV pipeline (new — `.sav` world file → stockpile data)

```
War.sav (+ map data)
  ▼ services/savefile_processor.py (SaveFileProcessor)
  ▼ services/sav_parser.py ──delegates──> fs-sav (Rust lib)
  ▼ faction-tagged dicts {faction, items, Z/ns timestamp}
  ▼ services/output_coordinator.py → handlers/*
```

SAV output is NOT validated through `Stockpile.model_validate`; `sav_parser`
owns the dict shape.

## Entry surfaces

| Surface | Module | Notes |
|---|---|---|
| CLI `fs` | `cli/app.py` (Typer) | `scan` `serve` `gui` `sav` |
| REST API | `api/server.py` (FastAPI) | see backend.md |
| Web UI | `api/web/routes.py` (Jinja) | upload form |
| Desktop GUI | `gui/app.py` (PySide6) | |
| OCR CLI | `fs_ocr/cli.py` | engine-only |
| Tooling | `fs_tools/cli.py`, `fs_tools/gui` | builders/extractors |

## Settings architecture

`core/settings/app_settings.py` → `AppSettings(BaseSettings)`, schema **v8**.
Top-level sections: `api_server`, `api_auth`, `external_tools`, `logging`,
`output`, `scanner`, `stockpile_types`, `database_builder`, `notifications`,
`gui`, `sav_processing`. (`OCRSettings`/`TemplateSettings` are sub-models
consumed by the engine/tooling, not top-level fields.)

Source priority (highest→lowest): env (`FS_<SECTION>__<KEY>`) → JSON file in
platform config dir → defaults. Stepwise migration via `ConfigMigrator`
(`CURRENT_VERSION = 8`).

## Event system

`core/events/bus.py` — `EventBus.emit(EventType, data)` / `subscribe(...)`.
Decouples NotificationService (Discord), logging, and memory metrics from the
pipeline. Events: server started/stopped, scan started/completed/failed, mod imported.

## Error handling

- Validate at boundaries (image size/format, Pydantic config, DB existence).
- Service layer raises specific exceptions; API maps to HTTP codes
  (401 auth, 429 rate, 503 Tesseract/DB).
- `ScanResult` envelope: `{success, data, error, processing_time_ms}`.

## Design decisions (rationale)

- **Two-phase + tiebreaker matching:** pHash kills 95%+ candidates cheaply; NCC
  scores the rest; pixel-diff tiebreaker separates near-identical items
  (e.g. Assembly Materials V vs VIII).
- **HDF5 over pickle:** structured, queryable, language-agnostic, no exec risk.
- **EventBus:** multiple async subscribers without tight coupling.
- **fs_ocr split:** isolates the OCR engine so a Rust impl can replace `_impl`
  behind the same `OCRScanner` API.

> NOTE: CLAUDE.md describes a future "named pipelines" config
> (`AppSettings.pipelines`, `general.mode`, migrator v11). That is NOT on this
> branch — current config is flat sections at schema v8.

## Key files

1. `fs_ocr/api.py` — public `OCRScanner`/`ScannerConfig`
2. `fs_ocr/_impl/coordinator.py` — pipeline orchestrator
3. `fs_ocr/_impl/template_manager.py` — icon matching
4. `foxhole_stockpiles/services/output_coordinator.py` — output routing
5. `foxhole_stockpiles/core/settings/app_settings.py` — configuration
