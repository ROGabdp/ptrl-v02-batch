from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


def _safe_ticker(ticker: str) -> str:
    return ticker.replace("^", "").replace(".", "_")


def load_or_update_local_csv(
    ticker: str,
    data_root: str | Path,
    start_date: str = "2000-01-01",
    auto_update: bool = True,
) -> pd.DataFrame | None:
    data_root = Path(data_root)
    data_root.mkdir(parents=True, exist_ok=True)
    csv_path = data_root / f"{_safe_ticker(ticker)}.csv"

    df: pd.DataFrame | None = None
    last_date = None
    need_update = auto_update

    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path, parse_dates=["Date"], index_col="Date")
            if not df.empty:
                last_date = df.index.max().date()
                if (date.today() - last_date).days <= 1:
                    need_update = False
        except Exception:
            df = None

    if not need_update:
        return df

    try:
        import yfinance as yf

        dl_start = start_date
        if df is not None and last_date is not None:
            dl_start = (pd.Timestamp(last_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        new_data = yf.download(ticker, start=dl_start, auto_adjust=True, progress=False)
        if len(new_data) == 0:
            return df
        if isinstance(new_data.columns, pd.MultiIndex):
            new_data.columns = new_data.columns.get_level_values(0)
        new_data.index.name = "Date"
        merged = pd.concat([df, new_data]) if df is not None else new_data
        merged = merged[~merged.index.duplicated(keep="last")].sort_index()
        merged.to_csv(csv_path)
        return merged
    except Exception:
        return df


def fetch_all_stock_data(cfg: dict[str, Any]) -> dict[str, pd.DataFrame]:
    tickers = list(cfg["universe"]["tickers"])
    benchmark = cfg["universe"]["benchmark"]
    data_root = cfg["data"]["data_root"]
    start_date = cfg["data"]["download_start"]
    auto_update = bool(cfg["data"].get("auto_update", True))
    warmup_days = int(cfg["splits"]["warmup_days"])

    out: dict[str, pd.DataFrame] = {}

    benchmark_df = load_or_update_local_csv(
        ticker=benchmark,
        data_root=data_root,
        start_date=start_date,
        auto_update=auto_update,
    )
    if benchmark_df is None or benchmark_df.empty:
        raise RuntimeError(f"Failed to load benchmark: {benchmark}")
    out[benchmark] = benchmark_df

    for ticker in tickers:
        df = load_or_update_local_csv(
            ticker=ticker,
            data_root=data_root,
            start_date=start_date,
            auto_update=auto_update,
        )
        if df is not None and len(df) > warmup_days:
            out[ticker] = df
    return out
