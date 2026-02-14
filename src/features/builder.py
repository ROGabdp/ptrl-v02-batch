from __future__ import annotations

import hashlib
import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange

from src.labels.targets import add_buy_targets


DEFAULT_FEATURE_COLS = [
    "Norm_Close",
    "Norm_Open",
    "Norm_High",
    "Norm_Low",
    "Norm_DC_Lower",
    "Norm_HA_Open",
    "Norm_HA_High",
    "Norm_HA_Low",
    "Norm_HA_Close",
    "Norm_SuperTrend_1",
    "Norm_SuperTrend_2",
    "Norm_RSI",
    "Norm_ATR_Change",
    "Norm_RS_Ratio",
    "RS_ROC_5",
    "RS_ROC_10",
    "RS_ROC_20",
    "RS_ROC_60",
    "RS_ROC_120",
    "Feat_MA20_Slope",
    "Feat_Trend_Gap",
    "Feat_Bias_MA20",
    "Feat_Dist_MA60",
    "Feat_Dist_MA240",
    "Feat_ATR_Ratio",
    "Feat_HV20",
    "Feat_Price_Pos",
    "Norm_K",
    "Norm_D",
    "Norm_DIF",
    "Norm_MACD",
    "Norm_OSC",
]


def calculate_heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    ha_close = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4.0
    ha_open = [df["Open"].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + ha_close.iloc[i - 1]) / 2.0)
    ha_open = pd.Series(ha_open, index=df.index)
    return pd.DataFrame(
        {
            "HA_Open": ha_open,
            "HA_High": pd.concat([df["High"], ha_open, ha_close], axis=1).max(axis=1),
            "HA_Low": pd.concat([df["Low"], ha_open, ha_close], axis=1).min(axis=1),
            "HA_Close": ha_close,
        }
    )


def calculate_supertrend(df: pd.DataFrame, length: int, multiplier: float) -> pd.Series:
    atr = AverageTrueRange(df["High"], df["Low"], df["Close"], window=length).average_true_range().bfill()
    hl2 = (df["High"] + df["Low"]) / 2
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr

    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    trend = np.zeros(len(df))
    for i in range(1, len(df)):
        if basic_upper.iloc[i] < final_upper.iloc[i - 1] or df["Close"].iloc[i - 1] > final_upper.iloc[i - 1]:
            final_upper.iloc[i] = basic_upper.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i - 1]
        if basic_lower.iloc[i] > final_lower.iloc[i - 1] or df["Close"].iloc[i - 1] < final_lower.iloc[i - 1]:
            final_lower.iloc[i] = basic_lower.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i - 1]
        if df["Close"].iloc[i] > final_upper.iloc[i - 1]:
            trend[i] = 1
        elif df["Close"].iloc[i] < final_lower.iloc[i - 1]:
            trend[i] = -1
        else:
            trend[i] = trend[i - 1]
    return pd.Series(np.where(trend == 1, final_lower, final_upper), index=df.index)


def build_feature_cache_key(
    cfg: dict[str, Any],
    ticker: str,
    data_start: str | None,
    data_end: str | None,
) -> str:
    payload = {
        "ticker": ticker,
        "universe_tickers": cfg["universe"]["tickers"],
        "benchmark": cfg["universe"]["benchmark"],
        "features": cfg["features"],
        "feature_cols": cfg["features"].get("feature_cols", DEFAULT_FEATURE_COLS),
        "label": cfg["label"],
        "splits": cfg["splits"],
        "data_range": [data_start, data_end],
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _cache_paths(cfg: dict[str, Any], ticker: str, key: str) -> Path:
    cache_root = Path(cfg["features"]["cache"]["cache_root"])
    cache_root.mkdir(parents=True, exist_ok=True)
    safe_ticker = ticker.replace("^", "").replace(".", "_")
    return cache_root / f"{safe_ticker}_{key[:16]}.pkl"


def build_features_for_ticker(
    cfg: dict[str, Any],
    ticker: str,
    df_in: pd.DataFrame,
    benchmark_df: pd.DataFrame | None,
    use_cache: bool = True,
) -> tuple[pd.DataFrame, str]:
    data_start = df_in.index.min().strftime("%Y-%m-%d") if len(df_in) else None
    data_end = df_in.index.max().strftime("%Y-%m-%d") if len(df_in) else None
    cache_key = build_feature_cache_key(cfg, ticker, data_start, data_end)
    cache_path = _cache_paths(cfg, ticker, cache_key)

    if use_cache and cache_path.exists():
        with cache_path.open("rb") as f:
            return pickle.load(f), cache_key

    fcfg = cfg["features"]
    lcfg = cfg["label"]
    df = df_in.copy()

    dc_win = int(fcfg["donchian"]["upper_lower_window"])
    dc_fast = int(fcfg["donchian"]["upper_window_fast"])
    df["DC_Upper"] = df["High"].rolling(dc_win).max().shift(1).bfill()
    df["DC_Lower"] = df["Low"].rolling(dc_win).min().shift(1).bfill()
    df["DC_Upper_10"] = df["High"].rolling(dc_fast).max().shift(1).bfill()
    df["Signal_Buy_Filter"] = (df["High"] > df["DC_Upper_10"]).astype("int8")

    atr_windows = [int(x) for x in fcfg["atr"]["windows"]]
    df["ATR"] = AverageTrueRange(df["High"], df["Low"], df["Close"], window=atr_windows[1]).average_true_range()
    df["ATR_5"] = AverageTrueRange(df["High"], df["Low"], df["Close"], window=atr_windows[0]).average_true_range()
    df["ATR_20"] = AverageTrueRange(df["High"], df["Low"], df["Close"], window=atr_windows[2]).average_true_range()
    df["RSI"] = RSIIndicator(df["Close"], window=int(fcfg["rsi"]["window"])).rsi()

    ha = calculate_heikin_ashi(df)
    df["HA_Open"] = ha["HA_Open"]
    df["HA_High"] = ha["HA_High"]
    df["HA_Low"] = ha["HA_Low"]
    df["HA_Close"] = ha["HA_Close"]

    st1, st2 = fcfg["supertrend"]["variants"]
    df["SuperTrend_1"] = calculate_supertrend(df, int(st1["period"]), float(st1["multiplier"]))
    df["SuperTrend_2"] = calculate_supertrend(df, int(st2["period"]), float(st2["multiplier"]))

    base_price = df["DC_Upper"].replace(0, np.nan).bfill()
    for col in [
        "Close",
        "Open",
        "High",
        "Low",
        "DC_Lower",
        "HA_Open",
        "HA_High",
        "HA_Low",
        "HA_Close",
        "SuperTrend_1",
        "SuperTrend_2",
    ]:
        df[f"Norm_{col}"] = df[col] / base_price

    df["Norm_RSI"] = df["RSI"] / 100.0
    df["Norm_ATR_Change"] = (df["ATR"] / df["ATR"].shift(1)).fillna(1.0)

    ma20, ma60, ma120, ma240 = [int(x) for x in fcfg["moving_average"]["windows"]]
    df["MA20"] = df["Close"].rolling(ma20).mean()
    df["MA60"] = df["Close"].rolling(ma60).mean()
    df["MA120"] = df["Close"].rolling(ma120).mean()
    df["MA240"] = df["Close"].rolling(ma240).mean()
    df["Feat_MA20_Slope"] = (df["MA20"] / df["MA20"].shift(1) - 1).fillna(0)
    df["Feat_Trend_Gap"] = ((df["MA20"] - df["MA240"]) / df["MA240"]).fillna(0)
    df["Feat_Bias_MA20"] = ((df["Close"] - df["MA20"]) / df["MA20"]).fillna(0)
    df["Feat_Dist_MA60"] = ((df["Close"] - df["MA60"]) / df["MA60"]).fillna(0)
    df["Feat_Dist_MA240"] = ((df["Close"] - df["MA240"]) / df["MA240"]).fillna(0)

    df["Feat_ATR_Ratio"] = (df["ATR_5"] / (df["ATR_20"] + 1e-9)).fillna(1.0)
    hv_window = int(fcfg["volatility_proxy"]["hv_window"])
    log_returns = np.log(df["Close"] / df["Close"].shift(1))
    df["Feat_HV20"] = (log_returns.rolling(hv_window).std() * np.sqrt(252)).clip(0, 1).fillna(0.3)
    pos_win = int(fcfg["volatility_proxy"]["price_pos_window"])
    high_n = df["High"].rolling(pos_win).max()
    low_n = df["Low"].rolling(pos_win).min()
    df["Feat_Price_Pos"] = ((df["Close"] - low_n) / (high_n - low_n + 1e-9)).fillna(0.5)

    k_window = int(fcfg["kd"]["k_window"])
    d_window = int(fcfg["kd"]["d_window"])
    low_min = df["Low"].rolling(k_window).min()
    high_max = df["High"].rolling(k_window).max()
    rsv = ((df["Close"] - low_min) / (high_max - low_min + 1e-9)) * 100
    df["K_raw"] = rsv.rolling(d_window).mean()
    df["D_raw"] = df["K_raw"].rolling(d_window).mean()
    df["Norm_K"] = (df["K_raw"] / 100.0).fillna(0.5)
    df["Norm_D"] = (df["D_raw"] / 100.0).fillna(0.5)

    mcfg = fcfg["macd"]
    ema_fast = df["Close"].ewm(span=int(mcfg["fast"]), adjust=False).mean()
    ema_slow = df["Close"].ewm(span=int(mcfg["slow"]), adjust=False).mean()
    df["DIF"] = ema_fast - ema_slow
    df["MACD_Signal"] = df["DIF"].ewm(span=int(mcfg["signal"]), adjust=False).mean()
    df["OSC"] = df["DIF"] - df["MACD_Signal"]
    df["Norm_DIF"] = (df["DIF"] / df["Close"]).fillna(0)
    df["Norm_MACD"] = (df["MACD_Signal"] / df["Close"]).fillna(0)
    df["Norm_OSC"] = (df["OSC"] / df["Close"]).fillna(0)

    if benchmark_df is not None:
        bench_close = benchmark_df["Close"].reindex(df.index).ffill()
        df["RS_Raw"] = df["Close"] / bench_close
        rs_win = int(fcfg["rs"]["norm_window"])
        rs_min = df["RS_Raw"].rolling(rs_win).min()
        rs_max = df["RS_Raw"].rolling(rs_win).max()
        df["Norm_RS_Ratio"] = ((df["RS_Raw"] - rs_min) / ((rs_max - rs_min).replace(0, np.nan) + 1e-9)).fillna(0.5)
        for period in [int(p) for p in fcfg["rs"]["roc_windows"]]:
            df[f"RS_ROC_{period}"] = df["RS_Raw"].pct_change(period).fillna(0)
    else:
        df["Norm_RS_Ratio"] = 0.5
        for period in [int(p) for p in fcfg["rs"]["roc_windows"]]:
            df[f"RS_ROC_{period}"] = 0.0

    df = add_buy_targets(
        df=df,
        horizon_days=int(lcfg["horizon_days"]),
        threshold=float(lcfg["threshold"]),
        future_price_field=str(lcfg.get("future_price_field", "High")),
        include_today=bool(lcfg.get("include_today", False)),
    )

    feature_cols = cfg["features"].get("feature_cols") or DEFAULT_FEATURE_COLS
    df = df.dropna(subset=["MA240"])
    df = df.dropna(subset=[c for c in feature_cols if c in df.columns] + ["Next_Max_Return"])

    if use_cache:
        with cache_path.open("wb") as f:
            pickle.dump(df, f)
    return df, cache_key


def build_all_features(
    cfg: dict[str, Any],
    raw_data: dict[str, pd.DataFrame],
    use_cache: bool = True,
) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    benchmark = cfg["universe"]["benchmark"]
    benchmark_df = raw_data[benchmark]
    feature_data: dict[str, pd.DataFrame] = {}
    cache_keys: dict[str, str] = {}
    for ticker, df in raw_data.items():
        feat, key = build_features_for_ticker(cfg, ticker, df, benchmark_df, use_cache=use_cache)
        feature_data[ticker] = feat
        cache_keys[ticker] = key
    return feature_data, cache_keys
