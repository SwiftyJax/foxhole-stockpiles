"""Version and git information utilities."""

import subprocess
from pathlib import Path


def _read_git_info_from_file() -> dict[str, str] | None:
    """Read git info from .git_info file (created during Docker build).

    Returns:
        dict with git info if file exists and is valid, None otherwise
    """
    try:
        git_info_file = Path(__file__).parent.parent.parent / ".git_info"
        if not git_info_file.exists():
            return None

        git_info = {}
        with open(git_info_file) as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    # Map file keys to dict keys
                    if key == "GIT_COMMIT_HASH":
                        git_info["hash"] = value
                    elif key == "GIT_COMMIT_SHORT_HASH":
                        git_info["short_hash"] = value
                    elif key == "GIT_COMMIT_DATE":
                        git_info["date"] = value
                    elif key == "GIT_DIRTY":
                        git_info["dirty"] = value

        # Validate we have all required keys
        if all(k in git_info for k in ["hash", "short_hash", "date", "dirty"]):
            return git_info

        return None

    except (OSError, ValueError):
        return None


def get_git_info() -> dict[str, str]:
    """Get git commit information.

    Tries to read from .git_info file first (Docker build),
    then falls back to git commands (development).

    Returns:
        dict with keys: hash, short_hash, date, dirty
        Returns 'unknown' for values if git is not available
    """
    # Try reading from file first (Docker build)
    file_info = _read_git_info_from_file()
    if file_info:
        return file_info

    # Fall back to git commands (development)
    try:
        # Check if we're in a git repository
        git_dir = Path(__file__).parent.parent.parent / ".git"
        if not git_dir.exists():
            return {
                "hash": "unknown",
                "short_hash": "unknown",
                "date": "unknown",
                "dirty": "unknown",
            }

        # Get commit hash
        hash_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )
        commit_hash = hash_result.stdout.strip()

        # Get short hash
        short_hash_result = subprocess.run(
            ["git", "rev-parse", "--short=7", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )
        short_hash = short_hash_result.stdout.strip()

        # Get commit date
        date_result = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=short"],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )
        commit_date = date_result.stdout.strip()

        # Check if working directory is dirty
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )
        is_dirty = "dirty" if status_result.stdout.strip() else "clean"

        return {
            "hash": commit_hash,
            "short_hash": short_hash,
            "date": commit_date,
            "dirty": is_dirty,
        }

    except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
        return {
            "hash": "unknown",
            "short_hash": "unknown",
            "date": "unknown",
            "dirty": "unknown",
        }


def get_version_info() -> str:
    """Get formatted version string with git info.

    Returns:
        Formatted version string like: "0.2.0 (git: abc1234, 2025-12-24, dirty)"
        or "0.2.0" if git info is not available
    """
    from foxhole_stockpiles import __version__

    git_info = get_git_info()

    if git_info["short_hash"] == "unknown":
        return __version__

    # Build version string
    version_parts = [__version__]
    git_parts = [f"git: {git_info['short_hash']}", git_info["date"]]

    if git_info["dirty"] == "dirty":
        git_parts.append("dirty")

    version_parts.append(f"({', '.join(git_parts)})")

    return " ".join(version_parts)
