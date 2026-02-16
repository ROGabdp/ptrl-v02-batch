from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel

class RegistryBestModel(BaseModel):
    ticker: str
    run_id: str
    model_path: str
    model_type: str  # "finetuned" or "base"
    precision: float
    lift: float
    buy_rate: float
    label_horizon_days: int
    label_threshold: float
    
class RegistryModelRow(BaseModel):
    ticker: str
    run_id: str
    model_path: Optional[str] = None
    precision: Optional[float] = None
    lift: Optional[float] = None
    buy_rate: Optional[float] = None
    tp: Optional[int] = None
    fp: Optional[int] = None
    # Add other metrics as needed based on CSV columns

class RunSummary(BaseModel):
    run_id: str
    tickers: List[str]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    status: str  # "COMPLETED", "FAILED", "RUNNING", "UNKNOWN"
    manifest_path: str

class RunDetail(BaseModel):
    run_id: str
    config: Dict[str, Any]
    metrics: Dict[str, Any]
    manifest: Dict[str, Any]
    models: Dict[str, List[str]] # {"base": [...], "finetuned": {"NVDA": [...]}}

class BacktestSummary(BaseModel):
    bt_run_id: str
    ticker: str
    model_path: str
    start_date: str
    end_date: str
    total_return: float
    cagr: float
    max_drawdown: float
    win_rate: float
    trade_count: int
    timestamp: Optional[datetime]

class EquityPoint(BaseModel):
    date: str
    portfolio_value: float
    benchmark_value: Optional[float] = None
    injected_cash: Optional[float] = None

class BacktestDetail(BaseModel):
    bt_run_id: str
    ticker: str
    config: Dict[str, Any]
    metrics: Dict[str, Any]
    summary_text: str
    end_date_summary_text: Optional[str]
    trades: List[Dict[str, Any]]  # Dowsampled or truncated list
    equity_curve: List[EquityPoint]
    plot_path: Optional[str] # Relative path to plot image if exists
