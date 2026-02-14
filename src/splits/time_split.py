from __future__ import annotations

from typing import Any

import pandas as pd


def filter_by_ranges(df: pd.DataFrame, ranges: list[list[str]]) -> pd.DataFrame:
    mask = pd.Series(False, index=df.index)
    for start, end in ranges:
        mask |= (df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))
    return df[mask]


def get_valid_train_ranges(df_raw: pd.DataFrame, train_ranges: list[list[str]], warmup_days: int) -> list[list[str]]:
    if len(df_raw) == 0:
        return []
    first_valid_date = df_raw.index[0] + pd.Timedelta(days=warmup_days)
    valid: list[list[str]] = []
    for start, end in train_ranges:
        s, e = pd.Timestamp(start), pd.Timestamp(end)
        if e < first_valid_date:
            continue
        actual_start = max(s, first_valid_date)
        if actual_start < e:
            valid.append([actual_start.strftime("%Y-%m-%d"), end])
    return valid


def split_train_val(
    cfg: dict[str, Any],
    raw_data: dict[str, pd.DataFrame],
    feature_data: dict[str, pd.DataFrame],
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame], dict[str, str]]:
    warmup = int(cfg["splits"]["warmup_days"])
    train_ranges = cfg["splits"]["train_ranges"]
    val_start, val_end = cfg["splits"]["val_range"]
    benchmark = cfg["universe"]["benchmark"]

    train_out: dict[str, pd.DataFrame] = {}
    val_out: dict[str, pd.DataFrame] = {}
    cutoff_dates: dict[str, str] = {}

    for ticker, fdf in feature_data.items():
        if ticker == benchmark:
            continue
        valid_ranges = get_valid_train_ranges(raw_data[ticker], train_ranges, warmup)
        if not valid_ranges:
            continue
        train_df = filter_by_ranges(fdf, valid_ranges)
        val_df = fdf[(fdf.index >= pd.Timestamp(val_start)) & (fdf.index <= pd.Timestamp(val_end))]
        if len(train_df) <= 100:
            continue
        train_out[ticker] = train_df
        val_out[ticker] = val_df if len(val_df) > 50 else train_df
        cutoff_dates[ticker] = raw_data[ticker].index.max().strftime("%Y-%m-%d")

    return train_out, val_out, cutoff_dates
