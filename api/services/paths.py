import os
from pathlib import Path

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

def resolve_path(path_str: str) -> Path:
    """
    Securely resolve a path string relative to BASE_DIR.
    Prevents path traversal attacks.
    """
    # Join with base dir
    full_path = (BASE_DIR / path_str).resolve()
    
    # Check if the resolved path is within BASE_DIR
    if not str(full_path).startswith(str(BASE_DIR)):
        raise ValueError(f"Access denied: Path {path_str} is outside of project root.")
    
    return full_path

def safe_join(base: Path, *paths: str) -> Path:
    """
    Securely join paths ensuring the result is within the base.
    """
    full_path = (base.joinpath(*paths)).resolve()
    if not str(full_path).startswith(str(BASE_DIR)):
        raise ValueError("Access denied: Path traversal detected.")
    return full_path

def get_allow_write_paths() -> set[Path]:
    """Return set of explicitly allowed paths for writing."""
    return {
        (BASE_DIR / "configs" / "daily_watchlist.yaml").resolve(),
    }

def validate_write_path(path: Path) -> None:
    """
    Validate that a path is allowed for writing.
    1. Must be within BASE_DIR.
    2. Must be in the allowed write list OR inside reports/daily/runtime/
    """
    resolved = path.resolve()
    if not str(resolved).startswith(str(BASE_DIR.resolve())):
         raise ValueError("Access denied: Path must be within project root.")
    
    # Specific allow list
    allowed_files = get_allow_write_paths()
    if resolved in allowed_files:
        return

    # Allow writing to daily runtime dir
    daily_runtime = (BASE_DIR / "reports" / "daily" / "runtime").resolve()
    if str(resolved).startswith(str(daily_runtime)):
        return

    raise ValueError(f"Access denied: Writing to {resolved} is not allowed.")
