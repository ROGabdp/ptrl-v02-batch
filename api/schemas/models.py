from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RegistryBestModel(BaseModel):
    ticker: str
    run_id: str
    model_path: str = Field(validation_alias="model_final_path")
    model_type: str = Field(validation_alias="mode")
    precision: Optional[float] = None
    lift: Optional[float] = None
    buy_rate: Optional[float] = None
    label_horizon_days: Optional[int] = None
    label_threshold: Optional[float] = None
    positive_rate: Optional[float] = None
    tp: Optional[int] = None
    fp: Optional[int] = None
    tn: Optional[int] = None
    fn: Optional[int] = None
    support: Optional[int] = None


class RegistryModelRow(BaseModel):
    ticker: str
    run_id: str
    mode: Optional[str] = None
    label_horizon_days: Optional[int] = None
    label_threshold: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1: Optional[float] = None
    accuracy: Optional[float] = None
    buy_rate: Optional[float] = None
    positive_rate: Optional[float] = None
    lift: Optional[float] = None
    tp: Optional[int] = None
    fp: Optional[int] = None
    tn: Optional[int] = None
    fn: Optional[int] = None
    support: Optional[int] = None
    model_final_path: Optional[str] = None
    config_path: Optional[str] = None
    metrics_path: Optional[str] = None
    manifest_path: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[str] = None


class RegistryModelsResponse(BaseModel):
    items: List[RegistryModelRow]
    total: int
    limit: int
    offset: int


class RunSummary(BaseModel):
    run_id: str
    tickers: List[str]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    status: str
    manifest_path: str


class RunDetail(BaseModel):
    run_id: str
    config: Dict[str, Any]
    metrics: Dict[str, Any]
    manifest: Dict[str, Any]
    models: Dict[str, Any]
    checkpoints_count: int = 0
    checkpoints_sample: List[str] = []


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
    trades: List[Dict[str, Any]]
    equity_curve: List[EquityPoint]
    plot_path: Optional[str]