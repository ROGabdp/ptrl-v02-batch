from __future__ import annotations

import pandas as pd


def add_buy_targets(
    df: pd.DataFrame,
    horizon_days: int,
    threshold: float,
    future_price_field: str = "High",
    include_today: bool = False,
) -> pd.DataFrame:
    out = df.copy()
    future_series = out[future_price_field]
    shift_n = 0 if include_today else 1
    max_future = (
        future_series.shift(-shift_n)
        .iloc[::-1]
        .rolling(horizon_days, min_periods=horizon_days)
        .max()
        .iloc[::-1]
    )
    out["Next_Max_Return"] = max_future / out["Close"] - 1.0
    out["Label_Buy"] = (out["Next_Max_Return"] >= threshold).astype("int8")
    return out
