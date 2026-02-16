from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from typing import List, Optional
from pathlib import Path
import os
from datetime import datetime

from api.services.readers import read_json_safe, read_yaml_safe, read_csv_downsampled, read_text_safe
from api.services.paths import resolve_path, safe_join, BASE_DIR
from api.schemas.models import BacktestSummary, BacktestDetail, EquityPoint

router = APIRouter(prefix="/backtests", tags=["Backtests"])

BACKTESTS_DIR = BASE_DIR / "backtests"

@router.get("/recent", response_model=List[BacktestSummary])
def get_recent_backtests(limit: int = 30):
    if not BACKTESTS_DIR.exists():
        return []
    
    backtests = []
    for bt_id in os.listdir(BACKTESTS_DIR):
        bt_path = BACKTESTS_DIR / bt_id
        if not bt_path.is_dir():
            continue
            
        metrics_path = bt_path / "metrics.json"
        
        # We need at least metrics to show a meaningful summary
        if not metrics_path.exists():
            continue
            
        metrics = read_json_safe(metrics_path)
        selection = read_json_safe(bt_path / "selection.json")
        config = read_yaml_safe(bt_path / "config.yaml")
        
        # Extract basic info
        ticker = selection.get("ticker", config.get("_ticker", "UNKNOWN"))
        model_path = selection.get("model_path", "UNKNOWN")
        bt_cfg = config.get("backtest", {})
        
        # Timestamp from folder mtime or parsing ID if it follows pattern bt_YYYYMMDD_HHMMSS
        timestamp = None
        try:
             parts = bt_id.split("__")[0].split("_") # bt, YYYYMMDD, HHMMSS
             if len(parts) >= 3:
                 dt_str = f"{parts[1]}_{parts[2]}"
                 timestamp = datetime.strptime(dt_str, "%Y%m%d_%H%M%S")
             else:
                 timestamp = datetime.fromtimestamp(bt_path.stat().st_mtime)
        except Exception:
             timestamp = datetime.fromtimestamp(bt_path.stat().st_mtime)

        backtests.append({
            "bt_run_id": bt_id,
            "ticker": ticker,
            "model_path": model_path,
            "start_date": str(bt_cfg.get("start", "")),
            "end_date": str(bt_cfg.get("end", "")),
            "total_return": metrics.get("total_return", 0.0),
            "cagr": metrics.get("cagr", 0.0),
            "max_drawdown": metrics.get("max_drawdown", 0.0),
            "win_rate": metrics.get("win_rate", 0.0),
            "trade_count": metrics.get("trade_count", 0),
            "timestamp": timestamp
        })
        
    backtests.sort(key=lambda x: x["timestamp"] or datetime.min, reverse=True)
    return backtests[:limit]

@router.get("/{bt_run_id}", response_model=BacktestDetail)
def get_backtest_detail(bt_run_id: str):
    bt_path = safe_join(BACKTESTS_DIR, bt_run_id)
    if not bt_path.exists():
        raise HTTPException(status_code=404, detail=f"Backtest {bt_run_id} not found")
    
    config = read_yaml_safe(bt_path / "config.yaml")
    metrics = read_json_safe(bt_path / "metrics.json")
    summary_text = read_text_safe(bt_path / "summary.txt")
    
    # End date summary
    # Scan for file pattern end_date_summary_*.txt
    end_date_summary_text = None
    for f in bt_path.glob("end_date_summary_*.txt"):
        end_date_summary_text = read_text_safe(f)
        break # Just take the first one
        
    # Trades (read downsampled)
    trades = read_csv_downsampled(bt_path / "trades.csv", max_points=100)
    
    # Equity Curve
    equity_data = read_csv_downsampled(bt_path / "equity.csv", max_points=2000)
    # Transform to list of EquityPoint
    equity_points = []
    for row in equity_data:
        # Check if benchmark_value exists, handle potential renames or missing cols
        bm_val = row.get("benchmark_value")
        if bm_val is None:
             # Try legacy name or just ignore
             pass
             
        equity_points.append(EquityPoint(
            date=str(row.get("date", "")),
            portfolio_value=float(row.get("portfolio_value", 0.0)),
            benchmark_value=float(bm_val) if bm_val is not None else None,
            injected_cash=float(row.get("injected_cash")) if row.get("injected_cash") is not None else None
        ))

    # Check for plot image
    plot_path = None
    if (bt_path / "plots" / "equity_curve.png").exists():
        plot_path = f"/api/backtests/{bt_run_id}/plot/equity.png"

    return {
        "bt_run_id": bt_run_id,
        "ticker": config.get("_ticker", "UNKNOWN"),
        "config": config,
        "metrics": metrics,
        "summary_text": summary_text,
        "end_date_summary_text": end_date_summary_text,
        "trades": trades,
        "equity_curve": equity_points,
        "plot_path": plot_path
    }

@router.get("/{bt_run_id}/equity", response_model=List[EquityPoint])
def get_backtest_equity(bt_run_id: str):
    bt_path = safe_join(BACKTESTS_DIR, bt_run_id)
    if not bt_path.exists():
        raise HTTPException(status_code=404, detail=f"Backtest {bt_run_id} not found")
        
    equity_data = read_csv_downsampled(bt_path / "equity.csv", max_points=2000)
    return [
        EquityPoint(
            date=str(row.get("date", "")),
            portfolio_value=float(row.get("portfolio_value", 0.0)),
            benchmark_value=float(row.get("benchmark_value")) if row.get("benchmark_value") is not None else None,
             injected_cash=float(row.get("injected_cash")) if row.get("injected_cash") is not None else None
        )
        for row in equity_data
    ]

@router.get("/{bt_run_id}/plot/equity.png")
def get_backtest_plot(bt_run_id: str):
    bt_path = safe_join(BACKTESTS_DIR, bt_run_id)
    plot_path = bt_path / "plots" / "equity_curve.png"
    if not plot_path.exists():
        raise HTTPException(status_code=404, detail="Equity plot not found")
    return FileResponse(plot_path)
