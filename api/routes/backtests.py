from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from typing import List, Optional
from pathlib import Path
import os
from datetime import datetime

from api.services.readers import read_json_safe, read_yaml_safe, read_csv_downsampled, read_text_safe, read_csv_safe
from api.services.paths import resolve_path, safe_join, BASE_DIR
from api.schemas.models import BacktestSummary, BacktestDetail, EquityPoint

router = APIRouter(prefix="/backtests", tags=["Backtests"])

BACKTESTS_DIR = BASE_DIR / "backtests"

def calculate_mdd_window(equity_data: List[dict]) -> Optional[dict]:
    """Calculate peak, trough, and recovery dates for the Max Drawdown."""
    if not equity_data:
        return None
        
    peak_val = -1.0
    peak_date = None
    
    mdd_val = 0.0
    mdd_peak_date = None
    mdd_trough_date = None
    
    # We need to find the specific peak-trough pair that causes valid MaxDD
    # This involves a single pass
    
    curr_peak_val = -1.0
    curr_peak_date = None
    
    # Track global max drawdown
    global_mdd = 0.0
    global_peak_date = None
    global_trough_date = None
    
    for row in equity_data:
        val = float(row.get("portfolio_value", 0))
        date = row.get("date")
        
        if val > curr_peak_val:
            curr_peak_val = val
            curr_peak_date = date
        
        dd = (curr_peak_val - val) / curr_peak_val if curr_peak_val > 0 else 0
        
        if dd > global_mdd:
            global_mdd = dd
            global_peak_date = curr_peak_date
            global_trough_date = date

    if global_mdd == 0:
        return None
        
    # Find recovery date: first date after trough where val >= peak
    recovery_date = None
    passed_trough = False
    for row in equity_data:
        date = row.get("date")
        if date == global_trough_date:
            passed_trough = True
            
        if passed_trough and float(row.get("portfolio_value", 0)) >= float(row.get("portfolio_value", 0) if not global_peak_date else -1): 
           # Wait, we need the value of global_peak_date. 
           # Easier logic: iterate again or store peak value.
           pass
           
    # Re-scan for recovery
    peak_val_at_mdd = 0
    # Perform a cleaner single pass or 2-pass
    # Pass 1: find MDD peak and trough
    # Pass 2: find recovery
    
    # Let's rewrite strictly:
    # 1. Calculate values and find Max DD
    values = [float(row.get('portfolio_value', 0)) for row in equity_data]
    dates = [row.get('date') for row in equity_data]
    
    if not values: return None

    max_val = values[0]
    max_idx = 0
    
    mdd = 0
    peak_idx = 0
    trough_idx = 0
    
    for i, v in enumerate(values):
        if v > max_val:
            max_val = v
            max_idx = i
        
        dd = (max_val - v) / max_val if max_val > 0 else 0
        if dd > mdd:
            mdd = dd
            peak_idx = max_idx
            trough_idx = i
            
    if mdd == 0:
        return None
        
    # Recovery: first index > trough_idx where value >= values[peak_idx]
    recovery_date = None
    peak_value = values[peak_idx]
    for i in range(trough_idx + 1, len(values)):
        if values[i] >= peak_value:
            recovery_date = dates[i]
            break
            
    return {
        "mdd_peak_date": dates[peak_idx],
        "mdd_trough_date": dates[trough_idx],
        "mdd_recovery_date": recovery_date
    }

def extract_strategy_summary(config: dict, ticker: str) -> dict:
    # Merge global strategy with per_ticker strategy
    strategy = config.get("strategy", {})
    per_ticker = config.get("per_ticker", {}).get(ticker, {})
    
    # Helper to deep get
    def get_param(path: str, default=None):
        keys = path.split(".")
        # Try per_ticker first
        val = per_ticker
        for k in keys:
            if isinstance(val, dict): val = val.get(k)
            else: val = None
        if val is not None: return val
        
        # Fallback to global
        val = strategy
        for k in keys:
             if isinstance(val, dict): val = val.get(k)
             else: val = None
        return val if val is not None else default

    return {
        "stop_loss_pct": get_param("exit.stop_loss_pct"),
        "take_profit_activation_pct": get_param("exit.take_profit_activation_pct"),
        "trail_stop_low_pct": get_param("exit.trail_stop_low_pct"),
        "trail_stop_high_pct": get_param("exit.trail_stop_high_pct"),
        "min_days_between_entries": get_param("entry.min_days_between_entries"),
        "use_market_filter": get_param("entry.market_filter.file_path") is not None, # Approximation
        "conf_thresholds": get_param("entry.conf_thresholds")
    }

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
        
    # Trades (read all for recent list, downsampled for chart if we were to plot them)
    # For recent trades list, we want the last few actual trades
    all_trades = read_csv_safe(bt_path / "trades.csv")
    recent_trades = []
    if all_trades:
        # Sort by entry date just in case, though usually sequential
        # Assuming CSV order is chronological
        raw_recent = all_trades[-3:]
        # Calculate holding days
        for t in raw_recent:
            entry = t.get("entry_date")
            exit_ = t.get("exit_date")
            holding = 0
            if entry and exit_:
                try:
                    d1 = datetime.strptime(str(entry), "%Y-%m-%d")
                    d2 = datetime.strptime(str(exit_), "%Y-%m-%d")
                    holding = (d2 - d1).days
                except:
                    pass
            recent_trades.append({
                "entry_date": entry,
                "exit_date": exit_,
                "pnl_pct": float(t.get("pnl_pct", 0.0)),
                "exit_reason": t.get("exit_reason"),
                "holding_days": holding
            })
            
    # Reverse to show newest on top
    recent_trades.reverse()

    # Equity Curve - Read ALL for MDD calc to be accurate
    full_equity_data = read_csv_safe(bt_path / "equity.csv")
    mdd_window = calculate_mdd_window(full_equity_data)
    
    # Downsample for frontend chart
    equity_curve_points = []
    step = max(1, len(full_equity_data) // 2000)
    for i in range(0, len(full_equity_data), step):
        row = full_equity_data[i]
        bm_val = row.get("benchmark_value")
        equity_curve_points.append(EquityPoint(
            date=str(row.get("date", "")),
            portfolio_value=float(row.get("portfolio_value", 0.0)),
            benchmark_value=float(bm_val) if bm_val is not None else None,
            injected_cash=float(row.get("injected_cash")) if row.get("injected_cash") is not None else None
        ))
    # Ensure last point is included
    if full_equity_data and (len(full_equity_data) - 1) % step != 0:
        row = full_equity_data[-1]
        bm_val = row.get("benchmark_value")
        equity_curve_points.append(EquityPoint(
            date=str(row.get("date", "")),
            portfolio_value=float(row.get("portfolio_value", 0.0)),
            benchmark_value=float(bm_val) if bm_val is not None else None,
            injected_cash=float(row.get("injected_cash")) if row.get("injected_cash") is not None else None
        ))

    # Strategy Summary
    ticker = config.get("_ticker", "UNKNOWN")
    strategy_summary = extract_strategy_summary(config, ticker)

    # Check for plot image
    plot_path = None
    if (bt_path / "plots" / "equity_curve.png").exists():
        plot_path = f"/api/backtests/{bt_run_id}/plot/equity.png"

    return {
        "bt_run_id": bt_run_id,
        "ticker": ticker,
        "config": config,
        "metrics": metrics,
        "summary_text": summary_text,
        "end_date_summary_text": end_date_summary_text,
        "trades": recent_trades, # API field name is 'trades' but using it for recent list now? 
                                 # strict schema says List[Any]. UI phase 1 didn't use it. 
                                 # Phase 1.5 'recent_trades' field exists.
                                 # Let's populate 'trades' with downsampled if needed, or just recent?
                                 # Phase 1.5 requirements said: "Backtest detail ... Recent 3 trades"
                                 # I'll populate 'recent_trades' field AND 'trades' field (for backward compat or full list if needed later)
                                 # The schema has 'recent_trades'. I will populate that.
                                 # The 'trades' field in schema is currently List[Any].
        "equity_curve": equity_curve_points,
        "plot_path": plot_path,
        "strategy_summary": strategy_summary,
        "recent_trades": recent_trades,
        "mdd_window": mdd_window
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
