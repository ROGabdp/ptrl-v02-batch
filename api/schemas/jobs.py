from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field

JobType = Literal["train", "backtest", "eval_metrics"]
JobStatus = Literal["QUEUED", "RUNNING", "SUCCESS", "FAILED"]


class Job(BaseModel):
    job_id: str
    job_type: JobType
    status: JobStatus
    created_at: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    command: List[str]
    cwd: str
    artifacts_hint: Optional[Dict[str, str]] = None
    log_path: str
    meta_path: str


class TrainJobRequest(BaseModel):
    config_path: str
    overrides: List[str] = Field(default_factory=list)
    dry_run: bool = False


class BacktestJobRequest(BaseModel):
    config_path: str
    tickers: Optional[List[str]] = None
    model_path: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    overrides: List[str] = Field(default_factory=list)
    dry_run: bool = False


class EvalMetricsJobRequest(BaseModel):
    run_id: str
    mode: Literal["base", "finetune"] = "finetune"
    dry_run: bool = False

