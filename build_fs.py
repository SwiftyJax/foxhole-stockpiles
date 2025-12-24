"""Build script for creating the unified 'fs' executable."""

import subprocess
import sys
from pathlib import Path


def build_fs_executable() -> None:
    """Build the unified fs executable."""
    project_root = Path(__file__).parent

    print("Building Unified Foxhole Stockpiles Tool")
    print("=" * 50)

    # Build comprehensive hidden imports
    hidden_imports = [
        # Core dependencies
        "cv2",
        "numpy",
        "numpy.core._methods",
        "numpy.lib.format",
        "pydantic",
        "pydantic.json_schema",
        "pydantic_settings",
        "pytesseract",
        # API Server dependencies
        "fastapi",
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "starlette",
        "starlette.routing",
        "starlette.middleware",
        "multipart",
        # Core package modules
        "foxhole_stockpiles",
        "foxhole_stockpiles.core",
        "foxhole_stockpiles.core.logging",
        "foxhole_stockpiles.core.utils",
        "foxhole_stockpiles.enums",
        "foxhole_stockpiles.enums.item_faction",
        "foxhole_stockpiles.enums.item_category",
        "foxhole_stockpiles.enums.supported_resolution",
        "foxhole_stockpiles.models",
        "foxhole_stockpiles.services",
        # API modules
        "foxhole_stockpiles.api",
        "foxhole_stockpiles.api.server",
        "foxhole_stockpiles.api.auth",
        # All command modules
        "foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner",
        "foxhole_stockpiles.commands.database_builder.database_builder",
        "foxhole_stockpiles.commands.generate_templates.generate_templates",
        "foxhole_stockpiles.commands.uasset_extractor.uasset_extractor",
        "foxhole_stockpiles.commands.candidate_inspector.candidate_inspector",
        "foxhole_stockpiles.commands.api_server.api_server",
    ]

    # Build PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name",
        "fs",
        "--console",
        "-m",
        "foxhole_stockpiles.commands.fs",
    ]

    # Add all hidden imports
    for import_name in hidden_imports:
        cmd.extend(["--hidden-import", import_name])

    # Exclude development dependencies
    exclude_modules = ["pytest", "mypy", "ruff", "pre_commit"]
    for module in exclude_modules:
        cmd.extend(["--exclude-module", module])

    print(f"Building with {len(hidden_imports)} hidden imports...")

    try:
        subprocess.run(cmd, cwd=project_root, check=True)

        # Check result
        exe_path = project_root / "dist" / "fs.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print("\nBuild successful!")
            print(f"Executable: {exe_path}")
            print(f"Size: {size_mb:.1f} MB")

            # Test the executable
            print("\nTesting executable...")

            # Test help
            result = subprocess.run([str(exe_path), "--help"], capture_output=True, text=True)
            if result.returncode == 0:
                print("Help command works")
            else:
                print("Help command failed")

            # Test subcommand help
            result = subprocess.run(
                [str(exe_path), "scanner", "--help"], capture_output=True, text=True
            )
            if result.returncode == 0:
                print("Scanner subcommand works")
            else:
                print("Scanner subcommand failed")

            print("\nfs.exe ready! Use: fs <command> [options]")

        else:
            print("Executable not found after build")

    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("PyInstaller not found. Install with: pip install pyinstaller")
        sys.exit(1)


if __name__ == "__main__":
    build_fs_executable()
