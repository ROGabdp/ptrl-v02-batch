import pandas as pd
import json
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional

def read_csv_safe(path: Path, limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
    """Reads a CSV file safely with limit and offset."""
    if not path.exists():
        return []
    
    # Read CSV
    # For large files, we might want to use chunksize, but for now assuming reasonable size or using limit
    df = pd.read_csv(path)
    
    # Replace NaN with None for JSON compatibility
    df = df.where(pd.notnull(df), None)
    
    # Apply limit and offset
    if limit is not None:
        return df.iloc[offset : offset + limit].to_dict(orient="records")
    return df.iloc[offset:].to_dict(orient="records")

def read_csv_downsampled(path: Path, max_points: int = 2000) -> List[Dict[str, Any]]:
    """Reads a CSV and downsamples it if it exceeds max_points."""
    if not path.exists():
        return []
    
    df = pd.read_csv(path)
    # Replace NaN with None
    df = df.where(pd.notnull(df), None)
    
    if len(df) > max_points:
        # Simple downsampling: take every Nth row
        step = len(df) // max_points
        df = df.iloc[::step]
    
    return df.to_dict(orient="records")

def read_json_safe(path: Path) -> Dict[str, Any]:
    """Reads a JSON file safely."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def read_yaml_safe(path: Path) -> Dict[str, Any]:
    """Reads a YAML file safely."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def read_text_safe(path: Path, max_lines: int = 1000) -> str:
    """Reads text file with line limit."""
    if not path.exists():
        return ""
    
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= max_lines:
                lines.append(f"\n... (truncated after {max_lines} lines)")
                break
            lines.append(line)
    return "".join(lines)
