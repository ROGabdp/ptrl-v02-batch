import json
import shutil
import tempfile
import yaml
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from api.schemas.daily import (
    DailyConfig,
    DailyConfigResponse,
    DailyConfigUpdate,
    DailyRunRequest,
    DailyBatchResponse,
    DailyJobItem,
)
from api.services.jobs import create_backtest_job
from api.services.paths import BASE_DIR, validate_write_path

# Path constants
CONFIG_PATH = BASE_DIR / "configs" / "daily_watchlist.yaml"
DAILY_REPORTS_DIR = BASE_DIR / "reports" / "daily"
RUNTIME_CONFIGS_DIR = DAILY_REPORTS_DIR / "runtime"

def _ensure_dirs():
    RUNTIME_CONFIGS_DIR.mkdir(parents=True, exist_ok=True)

def get_config() -> DailyConfigResponse:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config not found: {CONFIG_PATH}")
    
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            # Handle version wrapper if present, though schema expects direct fields? 
            # The file has "daily:" root. The schema DailyConfig expects fields like "tickers", "backtest".
            # So we need to look under "daily" key if it exists.
            if "daily" in data:
                config_data = data["daily"]
            else:
                config_data = data
                
            config = DailyConfig(**config_data)
            
            # Calculate a simple hash for collision detection/versioning if needed
            content_str = json.dumps(data, sort_keys=True)
            import hashlib
            config_hash = hashlib.sha256(content_str.encode("utf-8")).hexdigest()
            
            # Get last modified time
            mtime = CONFIG_PATH.stat().st_mtime
            saved_at = datetime.fromtimestamp(mtime).isoformat()
            
            return DailyConfigResponse(
                path=str(CONFIG_PATH.relative_to(BASE_DIR)).replace("\\", "/"),
                config=config,
                saved_at=saved_at,
                config_hash=config_hash
            )
    except Exception as e:
        raise ValueError(f"Failed to parse config: {e}")

def save_config(update: DailyConfigUpdate) -> DailyConfigResponse:
    validate_write_path(CONFIG_PATH)
    
    # Reconstruct the full YAML structure with "version: 1" and "daily:" root
    full_data = {
        "version": 1,
        "daily": update.config.dict(exclude_none=True)
    }
    
    # Write to temp file first for atomic operation
    fd, temp_path = tempfile.mkstemp(dir=CONFIG_PATH.parent, text=True)
    try:
        with open(fd, "w", encoding="utf-8") as f:
            # Use safe_dump with sort_keys=False to preserve order if possible (though dict order depends on python version)
            yaml.safe_dump(full_data, f, sort_keys=False, allow_unicode=True)
        
        # Atomic replace
        Path(temp_path).replace(CONFIG_PATH)
    except Exception as e:
        Path(temp_path).unlink(missing_ok=True)
        raise IOError(f"Failed to save config: {e}")
        
    return get_config()

def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursive merge of dictionaries.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result

def run_daily_batch(request: DailyRunRequest) -> DailyBatchResponse:
    _ensure_dirs()
    
    # 1. Load current config
    current_config_resp = get_config()
    daily_cfg = current_config_resp.config
    
    # 2. Determine Tickers
    tickers = request.tickers
    if not tickers:
        tickers = daily_cfg.tickers
    
    if not tickers:
        raise ValueError("No tickers specified in request or config.")
        
    # 3. Resolve Common Dates
    # Priority: Override > Config > Fallback (Today)
    
    # Start Date
    start_date = None
    if request.date_override and request.date_override.start:
        start_date = request.date_override.start
    elif daily_cfg.backtest.start:
        start_date = daily_cfg.backtest.start
    
    if not start_date:
        raise ValueError("Start date is required (in override or config).")
        
    # End Date
    end_date = None
    if request.date_override and request.date_override.end:
        end_date = request.date_override.end
    elif request.date_override and request.date_override.start:
        # If override start is provided but end is empty -> Default to Today
        # (As per user requirement: "若 date_override.start 有、date_override.end 空/null => end=today")
        end_date = date.today().isoformat()
    elif daily_cfg.backtest.end:
        end_date = daily_cfg.backtest.end
    else:
        # Fallback to Today
        end_date = date.today().isoformat()

    # 4. Create Batch ID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_hash = uuid4().hex[:8]
    batch_id = f"daily_{timestamp}__{batch_hash}"
    
    batch_dir = RUNTIME_CONFIGS_DIR / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    
    items: List[DailyJobItem] = []
    
    # 5. Generate Per-Ticker Config and Job
    for ticker in tickers:
        # A. Merge Strategy
        # Base strategy from daily config
        base_strategy = daily_cfg.strategy.dict(exclude_none=True)
        
        # Per-ticker override
        ticker_config = daily_cfg.per_ticker.get(ticker)
        ticker_override = {}
        if ticker_config and ticker_config.strategy:
             ticker_override = ticker_config.strategy.dict(exclude_none=True)
        
        merged_strategy = _deep_merge(base_strategy, ticker_override)
        
        # B. Construct Full Config for Run Backtest
        # Structure must match standard backtest config (strategies at root or under 'strategy' key?)
        # Based on configs/backtest/base.yaml:
        # Root keys: backtest, model, data, strategy, per_ticker (optional)
        
        # We construct a dedicated single-ticker config.
        # "per_ticker" section in the generated config is theoretically not needed if we merge it into "strategy".
        # However, scripts.run_backtest might expect `per_ticker` for specific overrides if logic depends on it.
        # But `scripts.run_backtest` mainly uses `strategy` + `per_ticker`.
        # To be safe and "Generated Config" style, we can put everything into `strategy` and leave `per_ticker` empty,
        # OR we can keep the merged strategy in `per_ticker` for this specific ticker.
        # 
        # Actually, `scripts.run_backtest` loads config, then looks for `per_ticker` block.
        # If we pre-merge, we can just put the final strategy in `strategy` block and have NO `per_ticker` block.
        # This is cleaner.
        
        runtime_config = {
            "version": 1,
            "backtest": daily_cfg.backtest.dict(exclude_none=True),
            "model": daily_cfg.model.dict(exclude_none=True),
            "data": daily_cfg.data.dict(exclude_none=True),
            "strategy": merged_strategy,
            # No per_ticker needed since we pre-merged
        }
        
        # Overwrite backtest start/end with resolved values
        runtime_config["backtest"]["start"] = start_date
        runtime_config["backtest"]["end"] = end_date
        
        # Also ensure tickers list in backtest section only has THIS ticker (or is ignored if CLI arg is passed)
        runtime_config["backtest"]["tickers"] = [ticker]
        
        # C. Write Runtime Config
        ticker_yaml_path = batch_dir / f"{ticker}.yaml"
        with open(ticker_yaml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(runtime_config, f, sort_keys=False, allow_unicode=True)
            
        # D. Create Job
        # We pass --config <runtime_path> --ticker <ticker>
        # Note: run_backtest still needs --ticker to know which one to run if config has multiple, 
        # or just to be explicit.
        
        # Note: jobs.create_backtest_job validation needs the path to be relative to repo or absolute.
        # _resolve_repo_path handles absolute paths if they are inside repo.
        rel_config_path = str(ticker_yaml_path.relative_to(BASE_DIR)).replace("\\", "/")
        
        # No extra overrides needed as they are baked into the config
        job_resp = create_backtest_job(
            config_path=rel_config_path,
            tickers=[ticker],
            model_path=None, # Use registry as defined in config
            start=None,      # Already in config
            end=None,        # Already in config
            overrides=[],
            dry_run=request.dry_run
        )
        
        items.append(DailyJobItem(
            ticker=ticker,
            job_id=job_resp.job_id,
            job_url=f"/jobs/{job_resp.job_id}",
            status=job_resp.status
        ))
        
    return DailyBatchResponse(
        batch_id=batch_id,
        created_at=datetime.now().isoformat(),
        items=items
    )
