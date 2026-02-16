"""回測輸出 — trades/equity CSV、metrics JSON、summary TXT、equity curve 圖。"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def save_trades_csv(trades: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not trades:
        path.write_text("# no trades\n", encoding="utf-8")
        return
    fieldnames = list(trades[0].keys())
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(trades)


def save_equity_csv(equity_curve: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not equity_curve:
        path.write_text("# no equity data\n", encoding="utf-8")
        return
    fieldnames = list(equity_curve[0].keys())
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(equity_curve)


def save_metrics_json(metrics: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)


def save_selection_json(selection: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(selection, f, indent=2, ensure_ascii=False, default=str)


def save_config_yaml(cfg: dict, path: Path) -> None:
    from src.config import dump_yaml
    dump_yaml(path, cfg)


def save_summary_txt(
    result: dict[str, Any],
    benchmark_metrics: dict[str, Any] | None,
    strategy: dict[str, Any],
    path: Path,
) -> None:
    """寫入人類可讀的回測摘要。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    m = result["metrics"]
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append(f"回測摘要 — {m['ticker']}")
    lines.append(f"期間: {m['start']} ~ {m['end']}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  總注入資金:     ${m['total_injected']:,.2f}")
    lines.append(f"  最終淨值:       ${m['final_value']:,.2f}")
    lines.append(f"  總報酬率:       {m['total_return']*100:+.2f}%")
    lines.append(f"  CAGR:           {m['cagr']*100:.2f}%")
    lines.append(f"  最大回撤:       {m['max_drawdown']*100:.2f}%")
    lines.append(f"  交易次數:       {m['trade_count']}")
    lines.append(f"  勝率:           {m['win_rate']*100:.1f}%")
    lines.append(f"  平均持倉天數:   {m['avg_hold_days']:.1f}")
    lines.append(f"  持倉比率:       {m['exposure_rate']*100:.1f}%")
    lines.append(f"  月均交易數:     {m['avg_trades_per_month']:.2f}")
    lines.append("")

    if benchmark_metrics:
        lines.append("-" * 40)
        lines.append(f"基準 (Benchmark B&H):")
        lines.append(f"  總報酬率:       {benchmark_metrics['total_return']*100:+.2f}%")
        lines.append(f"  CAGR:           {benchmark_metrics['cagr']*100:.2f}%")
        lines.append(f"  最大回撤:       {benchmark_metrics['max_drawdown']*100:.2f}%")
        lines.append("")
    else:
        lines.append("⚠️ Benchmark 資料不可用，未計算基準績效。")
        lines.append("")

    # 策略參數摘要
    lines.append("-" * 40)
    lines.append("策略參數:")
    entry = strategy.get("entry", {})
    exit_s = strategy.get("exit", {})
    for tier in entry.get("conf_thresholds", []):
        lines.append(f"  信心度 >= {tier['min_conf']*100:.0f}% → 買入 {tier['buy_frac']*100:.0f}%")
    lines.append(f"  市場濾網: {'ON' if entry.get('use_market_filter') else 'OFF'}")
    lines.append(f"  停損: {exit_s.get('stop_loss_pct', 0)*100:.1f}%")
    lines.append(f"  移動停利啟動: {exit_s.get('take_profit_activation_pct', 0)*100:.1f}%")
    lines.append(f"  回檔停利(低): {exit_s.get('trail_stop_low_pct', 0)*100:.1f}%")
    lines.append(f"  回檔停利(高): {exit_s.get('trail_stop_high_pct', 0)*100:.1f}%")
    lines.append("")

    # 持倉明細
    positions = result.get("positions", [])
    if positions:
        lines.append("-" * 40)
        lines.append(f"未平倉 ({len(positions)} 倉):")
        final_price = result["final_value"] - result.get("metrics", {}).get("total_injected", 0)  # approx
        for idx, pos in enumerate(positions, 1):
            ret = (float(result["equity_curve"][-1]["value"]) / pos["cost"] - 1) if pos["cost"] > 0 else 0
            lines.append(f"  #{idx} 買入 {pos['buy_date']} @ ${pos['buy_price']:.2f}"
                         f" | 股數 {pos['shares']:.4f} | 信心度 {pos['confidence']*100:.1f}%")

    lines.append("=" * 60)
    path.write_text("\n".join(lines), encoding="utf-8")


def save_end_date_summary(
    result: dict[str, Any],
    benchmark_metrics: dict[str, Any] | None,
    strategy: dict[str, Any],
    out_dir: Path,
    start: str,
    end: str,
) -> Path:
    """產出跟單用 end-date summary（對齊 legacy 格式）。"""
    ticker = result["metrics"]["ticker"]
    start_short = start.replace("-", "")
    end_short = end.replace("-", "")
    filename = f"end_date_summary_{ticker}_{start_short}_{end_short}.txt"
    path = out_dir / filename

    fs = result.get("final_state", {})
    m = result["metrics"]
    positions = result.get("positions", [])
    capital = fs.get("capital", 0.0)
    final_price = fs.get("price", 0.0)

    # 策略參數
    exit_cfg = strategy.get("exit", {})
    entry_cfg = strategy.get("entry", {})
    stop_loss_pct = float(exit_cfg.get("stop_loss_pct", 0.08))
    tp_activation = float(exit_cfg.get("take_profit_activation_pct", 0.20))
    trail_low = float(exit_cfg.get("trail_stop_low_pct", 0.08))
    trail_high = float(exit_cfg.get("trail_stop_high_pct", 0.17))
    high_profit_thr = float(exit_cfg.get("high_profit_threshold_pct", 0.25))
    conf_thresholds = sorted(
        entry_cfg.get("conf_thresholds", []),
        key=lambda x: x["min_conf"],
        reverse=True,
    )

    lines: list[str] = []
    final_date = fs.get("date")
    date_str = final_date.strftime("%Y-%m-%d") if hasattr(final_date, "strftime") else str(final_date)
    lines.append("=" * 60)
    lines.append(f"📅 報告日期: {date_str}")
    lines.append("=" * 60)

    # ─ 市場數據 ─
    lines.append(f"[市場數據 - {ticker}]")
    lines.append(f"📊 Close: ${final_price:.2f}")
    lines.append("-" * 30)
    lines.append("[市場數據 - Benchmark]")
    nq_close = fs.get("nasdaq_close")
    nq_120ma = fs.get("nasdaq_120ma")
    nq_above = fs.get("nasdaq_above_120ma", True)
    if nq_close is not None:
        lines.append(f"📊 Close: {nq_close:.2f}")
        lines.append(f"   120MA: {nq_120ma:.2f}" if nq_120ma is not None else "   120MA: N/A")
        lines.append(f"   Close > 120MA: {'✅ YES' if nq_above else '❌ NO'}")
    else:
        lines.append("⚠️ Benchmark 資料不可用")
    lines.append("-" * 30)

    # ─ 濾網與 AI 信號 ─
    action = fs.get("action", 0)
    confidence = fs.get("confidence", 0.0)
    allow_entry = fs.get("allow_entry", False)
    entry_type = fs.get("entry_type", "unknown")

    lines.append("[濾網與 AI 信號]")
    action_str = "BUY" if action == 1 else "WAIT"
    lines.append(f"   🤖 AI Action: {action_str} (Conf: {confidence*100:.1f}%)")
    lines.append(f"   📊 進場允許: {'✅ YES' if allow_entry else '❌ NO'} ({entry_type})")
    lines.append("-" * 50)

    # ─ 帳戶狀態 ─
    position_value = sum(p["shares"] * final_price for p in positions)
    total_value = capital + position_value
    total_injected = m["total_injected"]
    unrealized_pnl = position_value - sum(p["cost"] for p in positions) if positions else 0
    unrealized_pct = unrealized_pnl / sum(p["cost"] for p in positions) * 100 if positions and sum(p["cost"] for p in positions) > 0 else 0

    lines.append("[帳戶狀態]")
    lines.append(f"   💵 資金池餘額 (Cash):  ${capital:,.2f}")
    lines.append(f"   💎 持倉市值 (Value):   ${position_value:,.2f}")
    lines.append(f"   🏦 總資產 (Total):     ${total_value:,.2f}")
    lines.append(f"   📈 未實現損益:         ${unrealized_pnl:,.2f} ({unrealized_pct:+.2f}%)")
    lines.append(f"   💰 累計注入:           ${total_injected:,.2f}")
    lines.append(f"   📊 總報酬率:           {m['total_return']*100:+.2f}%")
    lines.append("-" * 50)

    # ─ 持倉明細 ─
    lines.append(f"[持倉明細] (共 {len(positions)} 倉)")
    for idx, pos in enumerate(positions, 1):
        bp = pos["buy_price"]
        shares = pos["shares"]
        cost = pos["cost"]
        cur_val = shares * final_price
        ret = (final_price / bp - 1) * 100
        highest = pos["highest_price"]
        conf = pos["confidence"]

        lines.append(f"   #{idx} 買入: {pos['buy_date']} @ ${bp:.2f} (信心: {conf*100:.1f}%)")
        lines.append(f"       股數: {shares:.4f} | 成本: ${cost:,.2f} | 市值: ${cur_val:,.2f}")
        lines.append(f"       報酬: {ret:+.2f}% | 最高價: ${highest:.2f}")

        hard_stop_price = bp * (1 - stop_loss_pct)
        trailing_trigger_price = bp * (1 + tp_activation)
        lines.append(f"       🛑 硬性停損: ${hard_stop_price:.2f}")

        hi_ret = highest / bp - 1
        if hi_ret >= tp_activation:
            cb_limit = trail_high if hi_ret >= high_profit_thr else trail_low
            trailing_stop_price = highest * (1 - cb_limit)
            lines.append(f"       📉 移動停利: ${trailing_stop_price:.2f} (回檔 {cb_limit*100:.0f}%)")
        else:
            lines.append(f"       📉 移動停利: (未啟動, 需漲至 ${trailing_trigger_price:.2f})")
        lines.append("")

    lines.append("-" * 50)

    # ─ 明日交易建議 ─
    lines.append("[🔮 明日交易建議 - 開盤執行]")
    lines.append("")

    # 買入建議
    if action == 1 and allow_entry:
        buy_frac = 0.0
        ratio_desc = ""
        for tier in conf_thresholds:
            if confidence >= tier["min_conf"]:
                buy_frac = tier["buy_frac"]
                ratio_desc = f">={tier['min_conf']*100:.0f}%"
                break

        if buy_frac > 0 and capital > 0:
            buy_amount = capital * buy_frac
            lines.append(f"   📈 【買入建議】: ✅ 建議買入")
            lines.append(f"      💰 建議買入金額: ${buy_amount:,.2f}")
            lines.append(f"      📊 資金比例: {buy_frac*100:.0f}% (AI 信心度 {ratio_desc})")
            lines.append(f"      💵 資金池餘額: ${capital:,.2f}")
        else:
            lines.append(f"   📈 【買入建議】: ❌ 不建議買入")
            lines.append(f"      ⚠️ 原因: 信心度不足 ({confidence*100:.1f}%)")
    else:
        lines.append(f"   📈 【買入建議】: ❌ 不建議買入")
        if action != 1:
            lines.append(f"      ⚠️ 原因: AI 未發出買入信號")
        elif not allow_entry:
            lines.append(f"      ⚠️ 原因: 市場濾網阻擋 ({entry_type})")

    lines.append("")
    lines.append("-" * 30)
    lines.append("")

    # 賣出監控
    lines.append("   📉 【賣出監控】: 停損/停利觸發價位")
    lines.append("")
    for idx, pos in enumerate(positions, 1):
        bp = pos["buy_price"]
        shares = pos["shares"]
        cur_val = shares * final_price
        highest = pos["highest_price"]

        hard_stop_price = bp * (1 - stop_loss_pct)
        hard_stop_value = shares * hard_stop_price

        lines.append(f"      #倉{idx} (市值 ${cur_val:,.2f}):")
        lines.append(f"         🛑 硬停損觸發: {ticker} 跌至 ${hard_stop_price:.2f} 時賣出")
        lines.append(f"            → 預計收回: ${hard_stop_value:,.2f}")

        hi_ret = highest / bp - 1
        if hi_ret >= tp_activation:
            cb_limit = trail_high if hi_ret >= high_profit_thr else trail_low
            trailing_stop_price = highest * (1 - cb_limit)
            trailing_value = shares * trailing_stop_price
            lines.append(f"         📉 移動停利: {ticker} 跌至 ${trailing_stop_price:.2f} 時賣出")
            lines.append(f"            → 預計收回: ${trailing_value:,.2f}")
        else:
            lines.append(f"         📉 移動停利: 未啟動 (需漲 {tp_activation*100:.0f}%)")
        lines.append("")

    # ─ 績效摘要 ─
    lines.append("=" * 60)
    lines.append("📊 績效摘要")
    lines.append("=" * 60)
    lines.append(f"   策略 ({ticker} AI Follow):")
    lines.append(f"      總報酬: {m['total_return']*100:+.2f}%")
    lines.append(f"      CAGR: {m['cagr']*100:.2f}%")
    lines.append(f"      MDD: {m['max_drawdown']*100:.2f}%")
    lines.append(f"      交易次數: {m['trade_count']}")
    lines.append(f"      勝率: {m['win_rate']*100:.1f}%")
    lines.append("")

    if benchmark_metrics:
        lines.append(f"   基準 (Benchmark B&H):")
        lines.append(f"      總報酬: {benchmark_metrics['total_return']*100:+.2f}%")
        lines.append(f"      CAGR: {benchmark_metrics['cagr']*100:.2f}%")
        lines.append(f"      MDD: {benchmark_metrics['max_drawdown']*100:.2f}%")
    else:
        lines.append("   ⚠️ Benchmark 資料不可用")

    lines.append("=" * 60)

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ─── Benchmark B&H ───────────────────────────────────────────────────


def calculate_benchmark_bh(
    benchmark_df: pd.DataFrame,
    start: str,
    end: str,
    initial_cash: float,
    yearly_contribution: float,
) -> dict[str, Any] | None:
    """計算 Benchmark Buy & Hold（同等資金注入）。"""
    import numpy as np

    bm = benchmark_df[
        (benchmark_df.index >= pd.Timestamp(start))
        & (benchmark_df.index <= pd.Timestamp(end))
    ].copy()
    if len(bm) == 0:
        return None

    dates = bm.index.tolist()
    closes = bm["Close"].values

    total_shares = initial_cash / float(closes[0])
    total_invested = initial_cash
    equity = []
    current_year = dates[0].year
    years_done = {current_year}

    for i, (d, p) in enumerate(zip(dates, closes)):
        if d.year != current_year:
            current_year = d.year
            if current_year not in years_done:
                total_shares += yearly_contribution / float(p)
                total_invested += yearly_contribution
                years_done.add(current_year)
        equity.append({"date": d.isoformat(), "value": total_shares * float(p)})

    final_val = total_shares * float(closes[-1])
    total_ret = (final_val - total_invested) / total_invested if total_invested else 0
    days_n = max(1, (dates[-1] - dates[0]).days)
    years_n = days_n / 365.0
    cagr = (final_val / total_invested) ** (1 / years_n) - 1 if years_n > 0 and total_invested > 0 else 0

    eq_vals = np.array([e["value"] for e in equity])
    rmax = np.maximum.accumulate(eq_vals)
    dd = (eq_vals - rmax) / np.where(rmax > 0, rmax, 1.0)
    max_dd = float(dd.min())

    return {
        "total_invested": total_invested,
        "final_value": round(final_val, 2),
        "total_return": round(total_ret, 6),
        "cagr": round(cagr, 6),
        "max_drawdown": round(max_dd, 6),
        "equity": equity,
    }


# ─── Equity Curve 圖 ─────────────────────────────────────────────────

def plot_equity_curve(
    result: dict[str, Any],
    benchmark_metrics: dict[str, Any] | None,
    backtest_cfg: dict[str, Any],
    out_dir: Path,
) -> Path | None:
    """繪製淨值曲線 PNG。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        # Windows 中文字體支援
        plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "SimHei", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False
    except ImportError:
        print("⚠️ matplotlib not available, skipping plot.")
        return None

    equity = result.get("equity_curve", [])
    if not equity:
        return None

    fig, ax = plt.subplots(figsize=(14, 8))

    # 策略曲線
    eq_dates = pd.to_datetime([e["date"] for e in equity])
    eq_vals = [e["value"] for e in equity]
    m = result["metrics"]
    ax.plot(eq_dates, eq_vals,
            label=f"{m['ticker']} Strategy ({m['total_return']:.0%})",
            linewidth=2, color="#4CAF50")

    # Benchmark
    if benchmark_metrics and benchmark_metrics.get("equity"):
        bm_eq = benchmark_metrics["equity"]
        bm_dates = pd.to_datetime([e["date"] for e in bm_eq])
        bm_vals = [e["value"] for e in bm_eq]
        ax.plot(bm_dates, bm_vals,
                label=f"Benchmark B&H ({benchmark_metrics['total_return']:.0%})",
                linewidth=2, linestyle="--", color="gray")

    # 注入參考線
    total_inj = m.get("total_injected", 0)
    if total_inj > 0:
        ax.axhline(y=total_inj, color="black", linestyle=":", alpha=0.3,
                    label=f"Total Injected (${total_inj:,.0f})")

    ax.set_title(f"{m['ticker']} AI Follow 策略淨值曲線\n{m['start']} ~ {m['end']}", fontsize=14)
    ax.set_xlabel("Date")
    ax.set_ylabel("Portfolio Value ($)")
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=0)

    plt.tight_layout()
    plots_dir = out_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    chart_path = plots_dir / "equity_curve.png"
    plt.savefig(str(chart_path), dpi=150, bbox_inches="tight")
    plt.close()
    return chart_path


# ─── 需要 pandas（模組層級 import 推遲到函式內） ─────────────────────
import pandas as pd
