"""Config-driven 回測 CLI。

用法：
  python -m scripts.run_backtest --config configs/backtest/base.yaml --ticker GOOGL
  python -m scripts.run_backtest --config configs/backtest/base.yaml --tickers NVDA,GOOGL,TSM
  python -m scripts.run_backtest --config configs/backtest/base.yaml --ticker GOOGL --dry-run
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.config import apply_overrides, dump_yaml, load_yaml, parse_set_values

# ─── 工具函式 ─────────────────────────────────────────────────────────

def _deep_merge(base: dict, override: dict) -> dict:
    """深層 merge：override 的值覆蓋 base，dict 遞迴合併。"""
    out = copy.deepcopy(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _bt_run_id(cfg: dict, ticker: str, model_path: str) -> str:
    """產生 bt_YYYYMMDD_HHMMSS__<hash8>。"""
    canon = json.dumps({
        "backtest": cfg.get("backtest", {}),
        "strategy": cfg.get("strategy", {}),
        "per_ticker": cfg.get("per_ticker", {}).get(ticker, {}),
        "ticker": ticker,
        "model_path": model_path,
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    h = hashlib.sha256(canon.encode()).hexdigest()[:8]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"bt_{ts}__{h}"


def _resolve_tickers(args, cfg: dict) -> list[str]:
    if args.ticker:
        return [args.ticker.upper()]
    if args.tickers:
        return [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    return [t.upper() for t in cfg.get("backtest", {}).get("tickers", [])]


def _get_merged_strategy(cfg: dict, ticker: str) -> dict:
    base_strat = cfg.get("strategy", {})
    overrides = cfg.get("per_ticker", {}).get(ticker, {})
    return _deep_merge(base_strat, overrides)


# ─── 主流程 ───────────────────────────────────────────────────────────

def run_single_ticker(
    ticker: str,
    cfg: dict[str, Any],
    *,
    registry_rows: list[dict] | None,
    model_path_override: str | None,
    mode: str,
    do_plot: bool,
    benchmark_symbol: str,
    dry_run: bool,
) -> dict[str, Any] | None:
    """對單一 ticker 執行完整回測流程。回傳 result dict。"""
    from src.backtest.selection import select_model_for_ticker

    # 1) 選模
    sel = select_model_for_ticker(
        ticker,
        registry_rows=registry_rows,
        mode=mode,
        model_path_override=model_path_override,
    )
    model_path = sel["model_path"]
    if not model_path:
        print(f"❌ {ticker}: 找不到模型路徑")
        return None

    # 2) 合併策略
    strategy = _get_merged_strategy(cfg, ticker)
    bt_cfg = cfg.get("backtest", {})

    # 3) bt_run_id
    bt_id = _bt_run_id(cfg, ticker, model_path)
    out_dir = Path("backtests") / bt_id

    # 4) stdout 摘要
    print(f"\n{'='*60}")
    print(f"  ticker:      {ticker}")
    print(f"  model_path:  {model_path}")
    if sel.get("label_horizon_days") is not None:
        print(f"  label:       horizon_days={sel['label_horizon_days']}, threshold={sel['label_threshold']}")
    print(f"  start:       {bt_cfg.get('start')}")
    print(f"  end:         {bt_cfg.get('end')}")
    print(f"  bt_run_id:   {bt_id}")
    print(f"  output:      {out_dir.as_posix()}")
    print(f"{'='*60}")

    if dry_run:
        print("  [DRY-RUN] 不執行回測")
        data_cfg = cfg.get("data", {})
        if data_cfg.get("auto_update", True):
            print(f"  [資料更新] 將更新資料到 end={bt_cfg.get('end')}")
        _print_strategy_summary(strategy)
        return None

    # 5) 載入模型
    if not Path(model_path).exists():
        print(f"❌ 模型檔案不存在: {model_path}")
        return None

    from stable_baselines3 import PPO
    model = PPO.load(model_path, device="cpu")

    # 6) 決定特徵設定（優先 registry 的 train config）
    train_cfg = sel.get("train_cfg")
    data_cfg = cfg.get("data", {})
    if train_cfg:
        feature_cols = train_cfg.get("features", {}).get("feature_cols", [])
        features_cfg = train_cfg.get("features", {})
        universe_cfg = train_cfg.get("universe", {})
        splits_cfg = train_cfg.get("splits", {})
        label_cfg = train_cfg.get("label", {})
        print(f"  ✅ 使用訓練 config 的特徵設定 (feature_cols={len(feature_cols)} 欄)")
    else:
        print("  ⚠️ 找不到訓練 config，使用回測 config 的 data 設定")
        feature_cols = []
        features_cfg = {}
        universe_cfg = {}
        splits_cfg = {}
        label_cfg = {}

    # 建立用來呼叫 data/features 的 pseudo-config
    pseudo_cfg: dict[str, Any] = {
        "universe": universe_cfg if universe_cfg else {"benchmark": benchmark_symbol, "tickers": [ticker]},
        "data": data_cfg,
        "splits": splits_cfg if splits_cfg else {"warmup_days": 250, "train_ranges": [], "val_range": ["2000-01-01", "2099-12-31"]},
        "label": label_cfg if label_cfg else {"horizon_days": 20, "threshold": 0.10, "future_price_field": "High", "include_today": False},
        "features": features_cfg if features_cfg else {},
    }

    # 7) 載入資料
    from src.data.loader import load_or_update_local_csv

    bm_symbol = benchmark_symbol
    bm_df = None
    try:
        bm_df = load_or_update_local_csv(
            ticker=bm_symbol,
            data_root=data_cfg.get("data_root", "scripts/legacy/data/stocks"),
            start_date=data_cfg.get("download_start", "2000-01-01"),
            auto_update=bool(data_cfg.get("auto_update", True)),
        )
    except Exception as e:
        print(f"  ⚠️ Benchmark ({bm_symbol}) 載入失敗: {e}")

    if bm_df is None or bm_df.empty:
        print(f"  ⚠️ Benchmark ({bm_symbol}) 資料不可用，市場濾網將使用預設允許。")
        bm_df = None

    raw_df = load_or_update_local_csv(
        ticker=ticker,
        data_root=data_cfg.get("data_root", "scripts/legacy/data/stocks"),
        start_date=data_cfg.get("download_start", "2000-01-01"),
        auto_update=bool(data_cfg.get("auto_update", True)),
    )
    if raw_df is None or raw_df.empty:
        print(f"❌ {ticker}: 無法載入股價資料")
        return None

    # 8) 特徵建構
    from src.features.builder import build_features_for_ticker
    feature_df, _cache_key = build_features_for_ticker(
        cfg=pseudo_cfg,
        ticker=ticker,
        df_in=raw_df,
        benchmark_df=bm_df,
        use_cache=False,  # 回測不用快取，確保資料正確
        include_labels=False,  # 回測不需要 label，避免截斷尾端資料
    )

    if not feature_cols:
        # fallback：用 builder 預設
        from src.features.builder import DEFAULT_FEATURE_COLS
        feature_cols = list(DEFAULT_FEATURE_COLS)
        print(f"  ⚠️ 使用 builder 預設 feature_cols ({len(feature_cols)} 欄)")

    # 移除 feature NaN 造成的 warmup 區（回測不需要 label）
    missing_cols = [c for c in feature_cols if c not in feature_df.columns]
    if missing_cols:
        print(f"  ⚠️ 以下 feature_cols 不在 DataFrame 中，將忽略: {missing_cols}")
        feature_cols = [c for c in feature_cols if c in feature_df.columns]

    pre_len = len(feature_df)
    feature_df = feature_df.dropna(subset=feature_cols)
    warmup_dropped = pre_len - len(feature_df)
    if warmup_dropped > 0:
        print(f"  ℹ️ feature warmup 移除 {warmup_dropped} 列 NaN (剩餘 {len(feature_df)} 列)")
    if len(feature_df) == 0:
        print(f"  ❌ feature dropna 後無資料")
        return None

    print(f"  ℹ️ 資料範圍: {feature_df.index.min().strftime('%Y-%m-%d')} ~ {feature_df.index.max().strftime('%Y-%m-%d')}")

    # 9) 執行回測
    from src.backtest.engine import run_backtest
    result = run_backtest(
        model=model,
        feature_df=feature_df,
        benchmark_df=bm_df,
        feature_cols=feature_cols,
        strategy=strategy,
        backtest_cfg=bt_cfg,
        ticker=ticker,
    )

    # 10) Benchmark B&H
    from src.backtest.io import (
        calculate_benchmark_bh,
        plot_equity_curve,
        save_config_yaml,
        save_equity_csv,
        save_metrics_json,
        save_selection_json,
        save_summary_txt,
        save_trades_csv,
    )

    bm_metrics = None
    if bm_df is not None:
        try:
            bm_metrics = calculate_benchmark_bh(
                bm_df,
                start=bt_cfg["start"],
                end=bt_cfg["end"],
                initial_cash=float(bt_cfg.get("initial_cash", 2400)),
                yearly_contribution=float(bt_cfg.get("yearly_contribution", 2400)),
            )
        except Exception as e:
            print(f"  ⚠️ Benchmark B&H 計算失敗: {e}")

    # 11) 寫出產物
    out_dir.mkdir(parents=True, exist_ok=True)

    # config.yaml：紀錄實際生效的全部設定
    effective_cfg = copy.deepcopy(cfg)
    effective_cfg["_resolved_strategy"] = strategy
    effective_cfg["_ticker"] = ticker
    effective_cfg["_bt_run_id"] = bt_id
    save_config_yaml(effective_cfg, out_dir / "config.yaml")

    # selection.json
    sel_out = {
        "ticker": ticker,
        "model_path": model_path,
        "mode": mode,
        "label_horizon_days": sel.get("label_horizon_days"),
        "label_threshold": sel.get("label_threshold"),
        "registry_row": sel.get("registry_row"),
    }
    save_selection_json(sel_out, out_dir / "selection.json")

    save_trades_csv(result["trades"], out_dir / "trades.csv")
    save_equity_csv(result["equity_curve"], out_dir / "equity.csv")
    save_metrics_json(result["metrics"], out_dir / "metrics.json")
    save_summary_txt(result, bm_metrics, strategy, out_dir / "summary.txt")

    # end-date summary（跟單用）
    from src.backtest.io import save_end_date_summary
    eds_path = save_end_date_summary(
        result, bm_metrics, strategy, out_dir,
        start=bt_cfg["start"], end=bt_cfg["end"],
    )
    print(f"  ✅ 跟單摘要: {eds_path.as_posix()}")

    if do_plot:
        chart = plot_equity_curve(result, bm_metrics, bt_cfg, out_dir)
        if chart:
            print(f"  ✅ 淨值曲線: {chart.as_posix()}")

    # 12) stdout 績效摘要
    m = result["metrics"]
    print(f"\n  📊 {ticker} 績效:")
    print(f"     總報酬: {m['total_return']*100:+.2f}%  CAGR: {m['cagr']*100:.2f}%")
    print(f"     MDD: {m['max_drawdown']*100:.2f}%  交易: {m['trade_count']}  勝率: {m['win_rate']*100:.1f}%")
    print(f"     持倉比率: {m['exposure_rate']*100:.1f}%  月均交易: {m['avg_trades_per_month']:.2f}")
    print(f"  📂 輸出: {out_dir.as_posix()}")

    return result


def _print_strategy_summary(strategy: dict) -> None:
    entry = strategy.get("entry", {})
    exit_s = strategy.get("exit", {})
    print("  策略參數:")
    for tier in entry.get("conf_thresholds", []):
        print(f"    信心度 >= {tier['min_conf']*100:.0f}% → 買入 {tier['buy_frac']*100:.0f}%")
    print(f"    市場濾網: {'ON' if entry.get('use_market_filter') else 'OFF'}")
    print(f"    停損: {exit_s.get('stop_loss_pct', 0)*100:.1f}%")
    print(f"    移動停利啟動: {exit_s.get('take_profit_activation_pct', 0)*100:.1f}%")


# ─── CLI ──────────────────────────────────────────────────────────────

def main() -> None:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="Config-driven 回測工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", default="configs/backtest/base.yaml",
                        help="回測設定檔路徑 (預設: configs/backtest/base.yaml)")
    parser.add_argument("--ticker", help="單一 ticker (e.g. GOOGL)")
    parser.add_argument("--tickers", help="多 ticker，逗號分隔 (e.g. NVDA,GOOGL,TSM)")
    parser.add_argument("--start", help="回測起始日 YYYY-MM-DD（未指定則使用 config 預設 2017-10-16）")
    parser.add_argument("--end", help="回測結束日 YYYY-MM-DD（未指定則使用 config 預設；只給 --start 時自動使用今天）")
    parser.add_argument("--registry-best", default=None,
                        help="registry CSV 路徑 (預設從 config)")
    parser.add_argument("--model-path", default=None,
                        help="強制使用此模型路徑（不走 registry）")
    parser.add_argument("--mode", default=None, choices=["finetune", "base"],
                        help="模型模式 (預設: finetune)")
    parser.add_argument("--set", action="append", default=[],
                        help="覆寫 config，格式: key=value")
    parser.add_argument("--dry-run", action="store_true",
                        help="只印出摘要，不執行回測")
    parser.add_argument("--benchmark", default=None,
                        help="Benchmark 代碼 (預設: ^IXIC)")
    plot_group = parser.add_mutually_exclusive_group()
    plot_group.add_argument("--plot", action="store_true", dest="plot", default=True)
    plot_group.add_argument("--no-plot", action="store_false", dest="plot")

    args = parser.parse_args()

    # 載入 config
    cfg = load_yaml(args.config)
    if args.set:
        cfg = apply_overrides(cfg, parse_set_values(args.set))

    # CLI 覆寫日期
    bt = cfg.setdefault("backtest", {})
    if args.start:
        bt["start"] = args.start
    if args.end:
        bt["end"] = args.end
    elif args.start and not args.end:
        # 只給 --start → end = 今天
        today_str = date.today().strftime("%Y-%m-%d")
        bt["end"] = today_str
        print(f"  ℹ️ end 未指定 → 使用 today={today_str}")
    if args.benchmark:
        bt["benchmark"] = args.benchmark

    # 確認日期
    if "start" not in bt or "end" not in bt:
        print("❌ 必須指定 backtest.start 和 backtest.end（透過 config 或 --start/--end）")
        sys.exit(1)

    mode = args.mode or cfg.get("model", {}).get("mode", "finetune")
    benchmark_symbol = bt.get("benchmark", "^IXIC")

    # Registry
    registry_rows = None
    if not args.model_path:
        reg_path = args.registry_best or cfg.get("model", {}).get(
            "registry_best_path", "reports/registry/registry_best_by_ticker.csv"
        )
        from src.backtest.selection import load_registry_best
        registry_rows = load_registry_best(reg_path)

    # Tickers
    tickers = _resolve_tickers(args, cfg)
    if not tickers:
        print("❌ 未指定 ticker。使用 --ticker、--tickers 或在 config 中設定 backtest.tickers")
        sys.exit(1)

    print(f"\n🚀 回測啟動: {', '.join(tickers)}")
    print(f"   config: {args.config}")
    print(f"   期間: {bt['start']} ~ {bt['end']}")

    for ticker in tickers:
        try:
            run_single_ticker(
                ticker,
                cfg,
                registry_rows=registry_rows,
                model_path_override=args.model_path,
                mode=mode,
                do_plot=args.plot,
                benchmark_symbol=benchmark_symbol,
                dry_run=args.dry_run,
            )
        except Exception as e:
            print(f"❌ {ticker} 回測失敗: {e}")
            import traceback
            traceback.print_exc()

    print("\n✅ 回測完成")


if __name__ == "__main__":
    main()
