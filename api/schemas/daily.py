from datetime import date
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

# --- Daily Config Models ---

class EntryThreshold(BaseModel):
    min_conf: float
    buy_frac: float

class EntryStrategy(BaseModel):
    conf_thresholds: List[EntryThreshold] = []
    use_market_filter: bool = True
    min_days_between_entries: int = 0

class ExitStrategy(BaseModel):
    stop_loss_pct: Optional[float] = Field(None, ge=0.0, description="Positive value, e.g. 0.08 for 8% loss")
    take_profit_activation_pct: Optional[float] = Field(None, ge=0.0)
    trail_stop_low_pct: Optional[float] = Field(None, ge=0.0)
    trail_stop_high_pct: Optional[float] = Field(None, ge=0.0)
    high_profit_threshold_pct: Optional[float] = None

class StrategyConfig(BaseModel):
    entry: Optional[EntryStrategy] = None
    exit: Optional[ExitStrategy] = None

class BacktestConfig(BaseModel):
    start: Optional[str] = None  # YYYY-MM-DD
    end: Optional[str] = None    # YYYY-MM-DD
    initial_cash: float = 2400.0
    yearly_contribution: float = 2400.0
    benchmark: str = "^IXIC"

class ModelConfig(BaseModel):
    registry_best_path: str = "reports/registry/registry_best_by_ticker.csv"
    mode: str = "finetune"

class DataConfig(BaseModel):
    provider: str = "yfinance"
    auto_update: bool = True
    data_root: str = "scripts/legacy/data/stocks"
    download_start: str = "2000-01-01"

class PerTickerConfig(BaseModel):
    strategy: Optional[StrategyConfig] = None
    # Can expand for other per-ticker overrides if needed

class DailyConfig(BaseModel):
    tickers: List[str] = []
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    per_ticker: Dict[str, PerTickerConfig] = {}

# --- API Request/Response Models ---

class DailyConfigResponse(BaseModel):
    path: str
    config: DailyConfig
    saved_at: Optional[str] = None
    config_hash: Optional[str] = None

class DailyConfigUpdate(BaseModel):
    config: DailyConfig

class DateOverride(BaseModel):
    start: Optional[str] = None  # YYYY-MM-DD
    end: Optional[str] = None    # YYYY-MM-DD

class DailyRunRequest(BaseModel):
    tickers: Optional[List[str]] = None
    dry_run: bool = False
    date_override: Optional[DateOverride] = None

class DailyJobItem(BaseModel):
    ticker: str
    job_id: str
    job_url: str
    status: str

class DailyBatchResponse(BaseModel):
    batch_id: str
    created_at: str
    items: List[DailyJobItem]
