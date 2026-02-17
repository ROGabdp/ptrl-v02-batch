from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query

from api.schemas.models import RegistryBestModel, RegistryModelsResponse
from api.services.paths import BASE_DIR, safe_join
from api.services.readers import read_csv_safe

router = APIRouter(prefix="/registry", tags=["Registry"])

REGISTRY_PATH = BASE_DIR / "reports" / "registry"


def _f(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _i(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _parse_sort(sort: str) -> List[Tuple[str, bool]]:
    presets = {
        "precision_desc,lift_desc,buy_rate_asc,support_desc": [
            ("precision", True),
            ("lift", True),
            ("buy_rate", False),
            ("support", True),
        ],
        "lift_desc,precision_desc,buy_rate_asc,support_desc": [
            ("lift", True),
            ("precision", True),
            ("buy_rate", False),
            ("support", True),
        ],
        "precision_desc,support_desc,lift_desc,buy_rate_asc": [
            ("precision", True),
            ("support", True),
            ("lift", True),
            ("buy_rate", False),
        ],
    }
    return presets.get(sort, presets["precision_desc,lift_desc,buy_rate_asc,support_desc"])


def _apply_sort(rows: List[Dict[str, Any]], sort: str) -> List[Dict[str, Any]]:
    rules = _parse_sort(sort)
    ordered = list(rows)
    for field, desc in reversed(rules):
        if field in {"precision", "lift", "buy_rate"}:
            ordered.sort(
                key=lambda r: (_f(r.get(field)) is None, _f(r.get(field)) if _f(r.get(field)) is not None else 0.0),
                reverse=desc,
            )
        elif field == "support":
            ordered.sort(
                key=lambda r: (_i(r.get(field)) is None, _i(r.get(field)) if _i(r.get(field)) is not None else 0),
                reverse=desc,
            )
    return ordered


@router.get("/best", response_model=List[RegistryBestModel])
def get_best_registry():
    path = safe_join(REGISTRY_PATH, "registry_best_by_ticker.csv")
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Registry best file not found. Please run 'python -m scripts.index_runs --runs-dir runs --out-dir reports/registry'",
        )

    return read_csv_safe(path)


@router.get("/models", response_model=RegistryModelsResponse)
def get_registry_models(
    ticker: Optional[str] = Query(None),
    min_lift: Optional[float] = Query(None),
    min_precision: Optional[float] = Query(None),
    min_support: Optional[int] = Query(None),
    max_buy_rate: Optional[float] = Query(None),
    sort: str = Query("precision_desc,lift_desc,buy_rate_asc,support_desc"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    path = safe_join(REGISTRY_PATH, "registry_models.csv")
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Registry models file not found. Please run 'python -m scripts.index_runs --runs-dir runs --out-dir reports/registry'",
        )

    rows = read_csv_safe(path)

    if ticker:
        tk = ticker.upper()
        rows = [r for r in rows if tk in str(r.get("ticker", "")).upper()]

    if min_lift is not None:
        rows = [r for r in rows if (_f(r.get("lift")) is not None and _f(r.get("lift")) >= min_lift)]

    if min_precision is not None:
        rows = [r for r in rows if (_f(r.get("precision")) is not None and _f(r.get("precision")) >= min_precision)]

    if min_support is not None:
        rows = [r for r in rows if (_i(r.get("support")) is not None and _i(r.get("support")) >= min_support)]

    if max_buy_rate is not None:
        rows = [r for r in rows if (_f(r.get("buy_rate")) is not None and _f(r.get("buy_rate")) <= max_buy_rate)]

    sorted_rows = _apply_sort(rows, sort)
    total = len(sorted_rows)
    items = sorted_rows[offset : offset + limit]

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }