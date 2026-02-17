from fastapi import APIRouter, HTTPException, Body
from api.schemas.daily import (
    DailyConfigResponse, DailyConfigUpdate, DailyRunRequest, DailyBatchResponse
)
from api.services.daily import get_config, save_config, run_daily_batch

router = APIRouter(prefix="/daily", tags=["Daily"])

@router.get("/config", response_model=DailyConfigResponse)
def read_config():
    try:
        return get_config()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/config", response_model=DailyConfigResponse)
def update_config(update: DailyConfigUpdate):
    try:
        return save_config(update)
    except Exception as e:
        # Check for specific validation errors if needed, but 500 is safe for now
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/run-backtests", response_model=DailyBatchResponse)
def trigger_backtests(request: DailyRunRequest):
    try:
        return run_daily_batch(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
