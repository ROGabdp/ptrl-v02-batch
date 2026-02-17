from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from typing import List

from api.schemas.jobs import BacktestJobRequest, EvalMetricsJobRequest, Job, TrainJobRequest
from api.services.jobs import (
    create_backtest_job,
    create_eval_metrics_job,
    create_train_job,
    get_job,
    get_job_log,
    get_recent_jobs,
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/train", response_model=Job)
def create_train(request: TrainJobRequest):
    try:
        return create_train_job(
            config_path=request.config_path,
            overrides=request.overrides,
            dry_run=request.dry_run,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/backtest", response_model=Job)
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


@router.post("/eval-metrics", response_model=Job)
def create_eval_metrics(request: EvalMetricsJobRequest):
    try:
        return create_eval_metrics_job(
            run_id=request.run_id,
            mode=request.mode,
            dry_run=request.dry_run,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/recent", response_model=List[Job])
def recent_jobs(limit: int = Query(50, ge=1, le=200)):
    return get_recent_jobs(limit=limit)


@router.get("/{job_id}", response_model=Job)
def get_job_detail(job_id: str):
    try:
        return get_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found") from exc


@router.get("/{job_id}/log", response_class=PlainTextResponse)
def get_log(job_id: str):
    try:
        return get_job_log(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Log for job {job_id} not found") from exc

