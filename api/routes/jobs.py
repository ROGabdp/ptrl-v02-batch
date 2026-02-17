from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from api.schemas.jobs import (
    BacktestJobRequest,
    EvalMetricsJobRequest,
    JobDetailResponse,
    JobLogResponse,
    TrainJobRequest,
)
from api.services.jobs import (
    create_backtest_job,
    create_eval_metrics_job,
    create_train_job,
    get_job,
    get_job_log,
    get_recent_jobs,
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/train", response_model=JobDetailResponse)
def create_train(request: TrainJobRequest):
    try:
        return create_train_job(
            config_path=request.config_path,
            overrides=request.overrides,
            dry_run=request.dry_run,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/backtest", response_model=JobDetailResponse)
def create_backtest(request: BacktestJobRequest):
    try:
        return create_backtest_job(
            config_path=request.config_path,
            tickers=request.tickers,
            model_path=request.model_path,
            start=request.start,
            end=request.end,
            overrides=request.overrides,
            dry_run=request.dry_run,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/eval-metrics", response_model=JobDetailResponse)
def create_eval_metrics(request: EvalMetricsJobRequest):
    try:
        return create_eval_metrics_job(
            run_id=request.run_id,
            mode=request.mode,
            dry_run=request.dry_run,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/recent", response_model=List[JobDetailResponse])
def recent_jobs(
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
):
    return get_recent_jobs(limit=limit, status=status, job_type=job_type)


@router.get("/{job_id}", response_model=JobDetailResponse)
def get_job_detail(job_id: str):
    try:
        return get_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found") from exc


@router.get("/{job_id}/log", response_model=JobLogResponse)
def get_log(
    job_id: str,
    offset: int = Query(0, ge=0),
    tail: int = Query(20000, ge=1, le=2_000_000),
):
    try:
        return get_job_log(job_id, offset=offset, tail=tail)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Log for job {job_id} not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc