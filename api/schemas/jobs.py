from typing import List, Literal, Optional

from pydantic import BaseModel, Field

JobType = Literal["train", "backtest", "eval-metrics", "eval_metrics"]
JobStatus = Literal["QUEUED", "RUNNING", "SUCCESS", "FAILED"]


class JobArtifacts(BaseModel):
    run_id: Optional[str] = None
    run_dir: Optional[str] = None
    bt_run_id: Optional[str] = None
    bt_dir: Optional[str] = None
    artifacts_parse_error: Optional[str] = None


class JobRuntime(BaseModel):
    meta_path: str
    log_path: str


class JobDetailResponse(BaseModel):
    job_id: str
    job_type: JobType
    status: JobStatus
    created_at: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    duration_sec: Optional[float] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = None
    command: List[str]
    args_preview: str
    cwd: str
    artifacts: JobArtifacts = Field(default_factory=JobArtifacts)
    runtime: JobRuntime


class JobLogResponse(BaseModel):
    job_id: str
    content: str
    next_offset: int
    is_truncated: bool
    log_path: str


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
