from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pathlib import Path
import os
from datetime import datetime

from api.services.readers import read_json_safe, read_yaml_safe
from api.services.paths import resolve_path, safe_join, BASE_DIR
from api.schemas.models import RunSummary, RunDetail

router = APIRouter(prefix="/runs", tags=["Runs"])

RUNS_DIR = BASE_DIR / "runs"

@router.get("/recent", response_model=List[RunSummary])
def get_recent_runs(limit: int = 30):
    if not RUNS_DIR.exists():
         return []
    
    runs = []
    # Scan runs directory
    for run_id in os.listdir(RUNS_DIR):
        run_path = RUNS_DIR / run_id
        if not run_path.is_dir():
            continue
            
        manifest_path = run_path / "manifest.json"
        manifest = {}
        if manifest_path.exists():
            manifest = read_json_safe(manifest_path)
            
        # Fallback to config if manifest missing or for additional info
        config_path = run_path / "config.yaml"
        config = {}
        if config_path.exists():
            config = read_yaml_safe(config_path)
            
        # Determine status/time
        # Priority: Manifest > Config/File stats
        start_time = None
        end_time = None
        status = "UNKNOWN"
        
        if manifest:
            status = manifest.get("status", "UNKNOWN")
            start_str = manifest.get("start_time")
            end_str = manifest.get("end_time")
            
            # Infer status if missing but end_time exists
            if status == "UNKNOWN" and end_str:
                status = "COMPLETED"
            if start_str:
                try:
                    start_time = datetime.fromisoformat(start_str)
                except ValueError:
                    pass
            if end_str:
                try:
                    end_time = datetime.fromisoformat(end_str)
                except ValueError:
                    pass
        else:
            # Fallback using os.stat
            try:
                start_time = datetime.fromtimestamp(run_path.stat().st_ctime)
            except Exception:
                pass
        
        tickers = config.get("universe", {}).get("tickers", [])
        if not tickers and "finetune" in config.get("train", {}):
             tickers = config.get("train", {}).get("finetune", {}).get("tickers", [])

        runs.append({
            "run_id": run_id,
            "tickers": tickers,
            "start_time": start_time,
            "status": status,
            "end_time": end_time,
            "manifest_path": str(manifest_path.relative_to(BASE_DIR)) if manifest_path.exists() else ""
        })
    
    # Sort by start_time descending, handling None
    runs.sort(key=lambda x: x["start_time"] or datetime.min, reverse=True)
    
    return runs[:limit]

@router.get("/{run_id}", response_model=RunDetail)
def get_run_detail(run_id: str):
    run_path = safe_join(RUNS_DIR, run_id)
    if not run_path.exists():
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    config = read_yaml_safe(run_path / "config.yaml")
    metrics = read_json_safe(run_path / "metrics.json")
    manifest = read_json_safe(run_path / "manifest.json")
    
    # Models discovery
    models = {"base": [], "finetuned": {}}
    
    base_models_dir = run_path / "models" / "base"
    if base_models_dir.exists():
        models["base"] = [f.name for f in base_models_dir.iterdir() if f.name.endswith(".zip")]
        
    finetuned_dir = run_path / "models" / "finetuned"
    if finetuned_dir.exists():
        for ticker_dir in finetuned_dir.iterdir():
            if ticker_dir.is_dir():
                 models["finetuned"][ticker_dir.name] = [f.name for f in ticker_dir.iterdir() if f.name.endswith(".zip")]

    return {
        "run_id": run_id,
        "config": config,
        "metrics": metrics,
        "manifest": manifest,
        "models": models
    }
