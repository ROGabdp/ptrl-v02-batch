from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pathlib import Path

from api.services.readers import read_csv_safe
from api.services.paths import resolve_path, safe_join, BASE_DIR
from api.schemas.models import RegistryBestModel, RegistryModelRow

router = APIRouter(prefix="/registry", tags=["Registry"])

REGISTRY_PATH = BASE_DIR / "reports" / "registry"

@router.get("/best", response_model=List[RegistryBestModel])
def get_best_registry():
    path = safe_join(REGISTRY_PATH, "registry_best_by_ticker.csv")
    if not path.exists():
        raise HTTPException(
            status_code=404, 
            detail="Registry best file not found. Please run 'python -m scripts.index_runs --runs-dir runs --out-dir reports/registry'"
        )
    
    data = read_csv_safe(path)
    # Ensure all required fields are present or provide defaults if necessary
    # Assuming CSV structure matches pydantic model for now
    return data

@router.get("/models", response_model=List[RegistryModelRow])
def get_registry_models(
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    limit: int = 200,
    offset: int = 0
):
    path = safe_join(REGISTRY_PATH, "registry_models.csv")
    if not path.exists():
        raise HTTPException(
            status_code=404, 
            detail="Registry models file not found. Please run 'python -m scripts.index_runs --runs-dir runs --out-dir reports/registry'"
        )
    
    # Read all first for filtering (simplification for Phase 1)
    # For very large files, this would need optimized reading
    all_data = read_csv_safe(path)
    
    if ticker:
        ticker = ticker.upper()
        filtered_data = [row for row in all_data if row.get("ticker") == ticker]
    else:
        filtered_data = all_data
        
    # Apply limit/offset
    return filtered_data[offset : offset + limit]
