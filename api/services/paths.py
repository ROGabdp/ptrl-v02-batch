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

def get_project_root() -> Path:
    return BASE_DIR
