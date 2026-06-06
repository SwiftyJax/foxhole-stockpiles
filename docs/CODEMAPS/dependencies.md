<!-- Generated: 2026-06-06 | Branch: refactor/01-pyside6 | Token estimate: ~750 -->

# Dependencies & External Tools

Source of truth: `pyproject.toml`. Python **3.12+** (3.12/3.13 tested).

## Runtime dependencies

| Package | Min | Role |
|---|---|---|
| opencv-python-headless | 4.13.0.90 | image processing, template matching (NCC) |
| numpy | 2.4.5 | arrays / vectorized ops |
| pillow | 12.2.0 | image I/O |
| pytesseract | 0.3.13 | Tesseract wrapper (needs external binary) |
| h5py | 3.16.0 | HDF5 template DB |
| pydantic | 2.13.4 | models / validation |
| pydantic-settings | 2.14.1 | env + file config |
| fastapi | 0.136.1 | REST API |
| uvicorn[standard] | 0.47.0 | ASGI server |
| python-multipart | 0.0.29 | upload form parsing |
| jinja2 | 3.1.0 | web UI templates |
| slowapi | 0.1.9 | rate limiting |
| typer | 0.12.0 | CLI framework (`fs`, `fs-tools`) |
| **fs-sav** | 0.2.0 | **Rust `.sav` parser (new SAV feature)** |
| PySide6 | 6.6 | desktop GUI (LGPL) |
| httpx | 0.28.1 | async HTTP (webhooks) |
| discord-webhook | 1.3.1 | Discord notifications |
| psutil | 7.2.2 | process/memory utils |
| memory-profiler | 0.61.0 | memory profiling |

## Sibling Rust packages

- **fs-sav** (PyPI) — backs `services/sav_parser.py`. Already a dependency.
- **fs-ocr** (`../fs-ocr`, `StockpileScanner`/`ScanConfig`) — planned Rust
  replacement for the in-repo `fs_ocr/_impl`. The `OCRScanner` API and
  `ScannerInfo.implementation="python"|"rust"` are the swap seam. Not yet a dep.

## External binaries

| Tool | Required for | Platform | Integration |
|---|---|---|---|
| **Tesseract OCR** (5.x) | all OCR scans (fails at startup if missing) | any | `pytesseract`; custom model `tessdata/renner_numbers.traineddata` |
| **repak** | PAK extraction (`fs-tools`) | Win/Linux | `connectors/` + `fs_tools` |
| **umodel(.exe)** | UE asset conversion (`fs-tools`) | Windows | `connectors/` + `fs_tools` |

`ExternalToolsSettings`: `repak_path`, `umodel_path`
(env `FS_EXTERNAL_TOOLS__REPAK_PATH`, …). Extractor/converter detected as
Windows or Linux independently; Linux extractor + Windows converter is valid.

## Dev dependencies (`[project.optional-dependencies] dev`)

pytest 9.0.3 (+ asyncio 1.2, cov 7.1, xdist 3.8, qt 4.5), mypy 2.1 (strict),
ruff 0.15.13, pre-commit 4.6, type stubs (types-requests, types-psutil, h5py-stubs).

**Quality gates:** `ruff check` / `ruff format`; `mypy` (strict, pydantic plugin);
`pytest` (≥80% coverage target). Ruff lint: `E,W,F,I,B,UP,D`, line length 100,
preview rules on.

## Entry points (`pyproject.toml`)

```
[project.scripts]
fs        = foxhole_stockpiles.cli.app:main      # scan/serve/gui/sav
fs-ocr    = fs_ocr.cli:main
fs-tools  = fs_tools.cli:main
[project.gui-scripts]
fs-gui       = foxhole_stockpiles.gui.app:launch_gui
fs-tools-gui = fs_tools.gui:run_gui
```

## Platforms

Linux / Windows / macOS / WSL2. On WSL2, `/mnt/c/...` ↔ `C:\...` path
conversion for Windows-compiled tools; temp dirs use Windows-accessible paths
when a Windows tool is in the chain.

## Config examples

```jsonc
// platform config dir (per-binary)
{ "config_version": 8,
  "scanner": { "database_path": "...templates.h5", "custom_model": "renner_numbers" },
  "api_server": { "host": "0.0.0.0", "port": 8000 },
  "sav_processing": { /* save dir / map data resolution */ },
  "notifications": { "enabled": false } }
```
```bash
FS_SCANNER__DATABASE_PATH=/path/to/db.h5
FS_API_AUTH__AUTH_TYPE=bearer
FS_API_AUTH__BEARER_TOKEN=secret
```

## Licensing

Project MIT. Deps MIT/BSD/Apache; pytesseract GPLv3 (compatible);
PySide6 LGPLv3.

## Key files
1. `pyproject.toml` — declarations + entry points
2. `connectors/` — external tool integration (path conversion)
3. `services/sav_parser.py` — fs-sav binding
4. `core/settings/sections/external_tools.py` — tool paths
