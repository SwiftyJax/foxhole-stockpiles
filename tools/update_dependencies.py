#!/usr/bin/env python3
"""Update dependency versions in pyproject.toml based on pip list --outdated."""

import json
import re
import subprocess
import sys
from pathlib import Path


def get_outdated_packages() -> list[dict[str, str]]:
    """Get list of outdated packages from pip.

    Returns:
        List of dicts with 'name', 'version' (current), and 'latest_version' keys
    """
    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--outdated", "--format=json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error running pip list: {result.stderr}", file=sys.stderr)
        return []

    packages: list[dict[str, str]] = json.loads(result.stdout)
    return packages


def normalize_name(name: str) -> str:
    """Normalize package name for comparison (PEP 503)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def update_pyproject(
    pyproject_path: Path, outdated: list[dict[str, str]], dry_run: bool = False
) -> int:
    """Update version constraints in pyproject.toml.

    Args:
        pyproject_path: Path to pyproject.toml
        outdated: List of outdated packages from pip
        dry_run: If True, only print what would be changed

    Returns:
        Number of packages updated
    """
    content = pyproject_path.read_text()
    original_content = content
    updated_count = 0

    # Create lookup dict with normalized names
    outdated_lookup = {normalize_name(pkg["name"]): pkg for pkg in outdated}

    # Pattern to match dependency lines like: "package>=1.0.0" or "package[extra]>=1.0.0,<2.0.0"
    # Captures: package name, optional extras, operator, version, optional upper bound
    dep_pattern = re.compile(
        r'"([a-zA-Z0-9_-]+)(\[[^\]]+\])?(>=|<=|==|~=|>|<)([0-9]+\.[0-9]+\.?[0-9]*)(,[<>=!]+[0-9]+\.[0-9]+\.?[0-9]*)?"'
    )

    def replace_version(match: re.Match[str]) -> str:
        pkg_name = match.group(1)
        extras = match.group(2) or ""
        operator = match.group(3)
        old_version = match.group(4)
        upper_bound = match.group(5) or ""

        normalized = normalize_name(pkg_name)
        if normalized in outdated_lookup:
            new_version = outdated_lookup[normalized]["latest_version"]
            if old_version != new_version:
                nonlocal updated_count
                updated_count += 1
                action = "Would update" if dry_run else "Updating"
                print(f"  {action}: {pkg_name} {operator}{old_version} -> {operator}{new_version}")
                return f'"{pkg_name}{extras}{operator}{new_version}{upper_bound}"'

        return match.group(0)

    content = dep_pattern.sub(replace_version, content)

    if not dry_run and content != original_content:
        pyproject_path.write_text(content)
        print(f"\nUpdated {pyproject_path}")

    return updated_count


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Update dependency versions in pyproject.toml")
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be updated without making changes",
    )
    parser.add_argument(
        "--pyproject",
        type=Path,
        default=Path("pyproject.toml"),
        help="Path to pyproject.toml (default: ./pyproject.toml)",
    )
    args = parser.parse_args()

    if not args.pyproject.exists():
        print(f"Error: {args.pyproject} not found", file=sys.stderr)
        sys.exit(1)

    print("Checking for outdated packages...")
    outdated = get_outdated_packages()

    if not outdated:
        print("All packages are up to date!")
        return

    print(f"\nFound {len(outdated)} outdated package(s):")
    for pkg in outdated:
        print(f"  {pkg['name']}: {pkg['version']} -> {pkg['latest_version']}")

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Updating pyproject.toml...")
    updated = update_pyproject(args.pyproject, outdated, dry_run=args.dry_run)

    if updated == 0:
        print("\nNo matching dependencies found in pyproject.toml to update.")
        print("(Some packages may be transitive dependencies not listed directly)")
    else:
        print(f"\n{'Would update' if args.dry_run else 'Updated'} {updated} dependency version(s)")
        if not args.dry_run:
            print("\nRun 'pip install -e .[dev,gui,server]' to install the updated versions")


if __name__ == "__main__":
    main()
