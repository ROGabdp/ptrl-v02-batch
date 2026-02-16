"""回測引擎 — 執行單一 ticker 回測，產生 trades/equity/metrics。"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


# ─── 信心度提取 ────────────────────────────────────────────────────────

def get_action_confidence(model, obs: np.ndarray) -> tuple[int, float]:
    """回傳 (action, buy_confidence)。

    使用 SB3 PPO policy distribution 取得 action=1 (BUY) 的機率。
    """
    import torch

    obs_t = torch.as_tensor(obs.reshape(1, -1), dtype=torch.float32)
    with torch.no_grad():
        dist = model.policy.get_distribution(obs_t)
        probs = dist.distribution.probs.numpy()[0]
        action, _ = model.predict(obs, deterministic=True)
    return int(action), float(probs[1])


# ─── 市場濾網 ─────────────────────────────────────────────────────────

def prepare_market_filter(
    benchmark_df: pd.DataFrame | None,
    ticker_df: pd.DataFrame,
) -> pd.DataFrame:
    """計算市場濾網欄位並新增到 ticker_df 上。

    若 benchmark_df 為 None 則不加 Nasdaq 指標，只加 DC20。
    """
    out = ticker_df.copy()

    # 個股 20 日唐其安通道
    out["DC20_High"] = out["High"].rolling(20).max().shift(1)
    out["Ticker_Above_DC20"] = out["Close"] > out["DC20_High"]

    if benchmark_df is not None and len(benchmark_df) > 0:
        bm = benchmark_df.copy()
        bm["Nasdaq_120MA"] = bm["Close"].rolling(120).mean()
        bm["Nasdaq_Above_120MA"] = bm["Close"] > bm["Nasdaq_120MA"]
        for col in ["Nasdaq_120MA", "Nasdaq_Above_120MA"]:
            out[col] = bm[col].reindex(out.index).ffill()
        out["Nasdaq_Close"] = bm["Close"].reindex(out.index).ffill()
    else:
        out["Nasdaq_Above_120MA"] = True  # 無 benchmark → 預設允許
        out["Nasdaq_120MA"] = np.nan
        out["Nasdaq_Close"] = np.nan

    return out


def _check_entry_condition(row: pd.Series, use_market_filter: bool) -> tuple[bool, str]:
    """回傳 (allow, entry_type)。"""
    if not use_market_filter:
        return True, "no_filter"

    nasdaq_ok = bool(row.get("Nasdaq_Above_120MA", True))
    dc_ok = bool(row.get("Ticker_Above_DC20", False))

    if nasdaq_ok:
        return True, "bull_market"
    if dc_ok:
        return True, "breakout"
    return False, "blocked"


# ─── 回測主引擎 ───────────────────────────────────────────────────────

def run_backtest(
    *,
    model,
    feature_df: pd.DataFrame,
    benchmark_df: pd.DataFrame | None,
    feature_cols: list[str],
    strategy: dict[str, Any],
    backtest_cfg: dict[str, Any],
    ticker: str,
) -> dict[str, Any]:
    """對單一 ticker 執行完整回測。

    回傳 dict 包含 equity_curve, trades, metrics, positions, ...
    """
    start = backtest_cfg["start"]
    end = backtest_cfg["end"]
    initial_cash = float(backtest_cfg.get("initial_cash", 2400))
    yearly_contrib = float(backtest_cfg.get("yearly_contribution", 2400))

    # 策略參數
    entry_cfg = strategy.get("entry", {})
    exit_cfg = strategy.get("exit", {})
    conf_thresholds = sorted(
        entry_cfg.get("conf_thresholds", []),
        key=lambda x: x["min_conf"],
        reverse=True,
    )
    use_market_filter = bool(entry_cfg.get("use_market_filter", True))
    min_days_between = int(entry_cfg.get("min_days_between_entries", 0))

    stop_loss_pct = float(exit_cfg.get("stop_loss_pct", 0.08))
    tp_activation = float(exit_cfg.get("take_profit_activation_pct", 0.20))
    trail_low = float(exit_cfg.get("trail_stop_low_pct", 0.08))
    trail_high = float(exit_cfg.get("trail_stop_high_pct", 0.17))
    high_profit_thr = float(exit_cfg.get("high_profit_threshold_pct", 0.25))

    # 準備市場濾網
    df = prepare_market_filter(benchmark_df, feature_df)
    df = df[(df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))].copy()
    if len(df) == 0:
        return _empty_result(ticker, start, end)

    dates = df.index.tolist()
    closes = df["Close"].values
    features = df[feature_cols].values.astype(np.float32)

    # 狀態
    capital = initial_cash
    positions: list[dict] = []
    trades: list[dict] = []
    equity_curve: list[dict] = []
    injection_log: list[dict] = [{"date": dates[0].isoformat(), "amount": initial_cash, "type": "initial"}]
    last_buy_date: pd.Timestamp | None = None

    current_year = dates[0].year
    years_injected: set[int] = {current_year}
    days_in_position = 0

    for i in range(len(df)):
        date = dates[i]
        price = float(closes[i])
        row = df.iloc[i]

        # 年度注資
        if date.year != current_year:
            current_year = date.year
            if current_year not in years_injected:
                capital += yearly_contrib
                injection_log.append({"date": date.isoformat(), "amount": yearly_contrib, "type": "yearly"})
                years_injected.add(current_year)

        # 持倉市值
        pos_value = sum(p["shares"] * price for p in positions)
        equity_curve.append({
            "date": date.isoformat(),
            "value": capital + pos_value,
            "capital": capital,
            "position_value": pos_value,
        })

        if positions:
            days_in_position += 1

        # ── 出場檢查 ──
        to_remove: list[int] = []
        for idx, pos in enumerate(positions):
            bp = pos["buy_price"]
            cur_ret = price / bp - 1
            hi_ret = pos["highest_price"] / bp - 1
            dd_from_hi = (pos["highest_price"] - price) / pos["highest_price"]

            if price > pos["highest_price"]:
                pos["highest_price"] = price

            sell_reason = None
            if cur_ret <= -stop_loss_pct:
                sell_reason = "Hard Stop"
            elif hi_ret >= tp_activation:
                cb_limit = trail_high if hi_ret >= high_profit_thr else trail_low
                if dd_from_hi >= cb_limit:
                    sell_reason = "Trailing Stop"

            if sell_reason:
                sell_val = pos["shares"] * price
                profit = sell_val - pos["cost"]
                capital += sell_val
                trades.append({
                    "buy_date": pos["buy_date"],
                    "buy_price": bp,
                    "sell_date": date.isoformat(),
                    "sell_price": price,
                    "shares": pos["shares"],
                    "cost": pos["cost"],
                    "sell_value": sell_val,
                    "return": cur_ret,
                    "profit": profit,
                    "hold_days": (date - pd.Timestamp(pos["buy_date"])).days,
                    "exit_reason": sell_reason,
                    "entry_type": pos["entry_type"],
                    "confidence": pos["confidence"],
                })
                to_remove.append(idx)

        for idx in sorted(to_remove, reverse=True):
            positions.pop(idx)

        # ── 進場檢查 ──
        obs = features[i]
        if np.isnan(obs).any():
            continue
        action, confidence = get_action_confidence(model, obs)

        if action == 1:
            # min_days_between_entries 檢查
            if min_days_between > 0 and last_buy_date is not None:
                if (date - last_buy_date).days < min_days_between:
                    continue

            allow, entry_type = _check_entry_condition(row, use_market_filter)
            if allow:
                buy_frac = 0.0
                for tier in conf_thresholds:
                    if confidence >= tier["min_conf"]:
                        buy_frac = tier["buy_frac"]
                        break

                if buy_frac > 0 and capital > 0:
                    invest = capital * buy_frac
                    if invest >= price:  # 至少能買 1 股
                        shares = invest / price
                        cost = shares * price
                        capital -= cost
                        positions.append({
                            "shares": shares,
                            "buy_price": price,
                            "buy_date": date.isoformat(),
                            "cost": cost,
                            "highest_price": price,
                            "confidence": confidence,
                            "entry_type": entry_type,
                        })
                        last_buy_date = date

    # ── 回測結束統計 ──
    total_injected = sum(log["amount"] for log in injection_log)
    final_price = float(closes[-1])
    pos_value = sum(p["shares"] * final_price for p in positions)
    final_value = capital + pos_value

    days_total = max(1, (dates[-1] - dates[0]).days)
    years = days_total / 365.0
    total_return = (final_value - total_injected) / total_injected if total_injected else 0.0
    cagr = (final_value / total_injected) ** (1 / years) - 1 if years > 0 and total_injected > 0 else 0.0

    # Drawdown
    eq_vals = np.array([e["value"] for e in equity_curve])
    rolling_max = np.maximum.accumulate(eq_vals)
    drawdowns = (eq_vals - rolling_max) / np.where(rolling_max > 0, rolling_max, 1.0)
    max_dd = float(drawdowns.min())

    # 勝率
    wins = sum(1 for t in trades if t["return"] > 0)
    trade_count = len(trades)
    win_rate = wins / trade_count if trade_count else 0.0

    # 平均持倉天數
    if trades:
        avg_hold = sum(t["hold_days"] for t in trades) / trade_count
    else:
        avg_hold = 0.0

    # exposure_rate
    total_bars = len(equity_curve)
    exposure_rate = days_in_position / total_bars if total_bars > 0 else 0.0

    # 月均交易數
    months = years * 12
    avg_trades_per_month = trade_count / months if months > 0 else 0.0

    metrics = {
        "ticker": ticker,
        "start": start,
        "end": end,
        "total_injected": total_injected,
        "final_value": round(final_value, 2),
        "total_return": round(total_return, 6),
        "cagr": round(cagr, 6),
        "max_drawdown": round(max_dd, 6),
        "trade_count": trade_count,
        "win_rate": round(win_rate, 4),
        "avg_hold_days": round(avg_hold, 1),
        "exposure_rate": round(exposure_rate, 4),
        "avg_trades_per_month": round(avg_trades_per_month, 2),
    }

    # ── 最後一天狀態（跟單 summary 用）──
    final_row = df.iloc[-1]
    final_obs = features[-1]
    if not np.isnan(final_obs).any():
        final_action, final_confidence = get_action_confidence(model, final_obs)
    else:
        final_action, final_confidence = 0, 0.0
    final_allow, final_entry_type = _check_entry_condition(final_row, use_market_filter)

    final_state = {
        "date": dates[-1],
        "price": final_price,
        "action": final_action,
        "confidence": final_confidence,
        "allow_entry": final_allow,
        "entry_type": final_entry_type,
        "capital": capital,
        "nasdaq_close": float(final_row.get("Nasdaq_Close", 0)) if pd.notna(final_row.get("Nasdaq_Close")) else None,
        "nasdaq_120ma": float(final_row.get("Nasdaq_120MA", 0)) if pd.notna(final_row.get("Nasdaq_120MA")) else None,
        "nasdaq_above_120ma": bool(final_row.get("Nasdaq_Above_120MA", True)),
    }

    return {
        "ticker": ticker,
        "metrics": metrics,
        "equity_curve": equity_curve,
        "trades": trades,
        "positions": positions,
        "injection_log": injection_log,
        "total_injected": total_injected,
        "final_value": final_value,
        "final_state": final_state,
    }


def _empty_result(ticker: str, start: str, end: str) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "metrics": {
            "ticker": ticker, "start": start, "end": end,
            "total_injected": 0, "final_value": 0,
            "total_return": 0, "cagr": 0, "max_drawdown": 0,
            "trade_count": 0, "win_rate": 0, "avg_hold_days": 0,
            "exposure_rate": 0, "avg_trades_per_month": 0,
        },
        "equity_curve": [],
        "trades": [],
        "positions": [],
        "injection_log": [],
        "total_injected": 0,
        "final_value": 0,
        "final_state": {},
    }
