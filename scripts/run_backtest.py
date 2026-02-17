"""Config-driven ?葫 CLI??

?冽?嚗?
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

# ??? 撌亙?賢? ?????????????????????????????????????????????????????????

def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge nested dictionaries."""
    out = copy.deepcopy(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _bt_run_id(cfg: dict, ticker: str, model_path: str) -> str:
    """Generate backtest run id in bt_YYYYMMDD_HHMMSS__<hash8> format."""
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


# ??? 銝餅?蝔????????????????????????????????????????????????????????????

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
    """Run backtest for a single ticker and return result dict on success."""
    from src.backtest.selection import select_model_for_ticker

    # 1) ?豢芋
    sel = select_model_for_ticker(
        ticker,
        registry_rows=registry_rows,
        mode=mode,
        model_path_override=model_path_override,
    )
    model_path = sel["model_path"]
    if not model_path:
        print(f"[ERROR] {ticker}: model path not found")
        return None

    # 2) ?蔥蝑
    strategy = _get_merged_strategy(cfg, ticker)
    bt_cfg = cfg.get("backtest", {})

    # 3) bt_run_id
    bt_id = _bt_run_id(cfg, ticker, model_path)
    out_dir = Path("backtests") / bt_id

    # 4) stdout ??
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
        print("  [DRY-RUN] Skip actual execution")
        data_cfg = cfg.get("data", {})
        if data_cfg.get("auto_update", True):
            print(f"  [鞈??湔] 撠?啗?? end={bt_cfg.get('end')}")
        _print_strategy_summary(strategy)
        return None

    # 5) 頛璅∪?
    if not Path(model_path).exists():
        print(f"??璅∪?瑼?銝??? {model_path}")
        return None

    from stable_baselines3 import PPO
    model = PPO.load(model_path, device="cpu")

    # 6) 瘙箏??孵噩閮剖?嚗??registry ??train config嚗?
    train_cfg = sel.get("train_cfg")
    if not train_cfg and model_path_override:
        model_cfg_path = None
        for parent in Path(model_path).parents:
            candidate = parent / "config.yaml"
            if candidate.exists():
                model_cfg_path = candidate
                break
        if model_cfg_path:
            train_cfg = load_yaml(model_cfg_path)
            print(f"  [INFO] Loaded train config from model path: {model_cfg_path.as_posix()}")
    data_cfg = cfg.get("data", {})
    if train_cfg:
        feature_cols = train_cfg.get("features", {}).get("feature_cols", [])
        features_cfg = train_cfg.get("features", {})
        universe_cfg = train_cfg.get("universe", {})
        splits_cfg = train_cfg.get("splits", {})
        label_cfg = train_cfg.get("label", {})
        print(f"  ??雿輻閮毀 config ?敺菔身摰?(feature_cols={len(feature_cols)} 甈?")
    else:
        raise ValueError(f"Cannot resolve training config for model: {model_path}")

    # 撱箇??其??澆 data/features ??pseudo-config
    pseudo_cfg: dict[str, Any] = {
        "universe": universe_cfg if universe_cfg else {"benchmark": benchmark_symbol, "tickers": [ticker]},
        "data": data_cfg,
        "splits": splits_cfg if splits_cfg else {"warmup_days": 250, "train_ranges": [], "val_range": ["2000-01-01", "2099-12-31"]},
        "label": label_cfg if label_cfg else {"horizon_days": 20, "threshold": 0.10, "future_price_field": "High", "include_today": False},
        "features": features_cfg if features_cfg else {},
    }

    # 7) 頛鞈?
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
        print(f"  ?? Benchmark ({bm_symbol}) 頛憭望?: {e}")

    if bm_df is None or bm_df.empty:
        print(f"  [WARN] Benchmark ({bm_symbol}) data unavailable, proceed without benchmark")
        bm_df = None

    raw_df = load_or_update_local_csv(
        ticker=ticker,
        data_root=data_cfg.get("data_root", "scripts/legacy/data/stocks"),
        start_date=data_cfg.get("download_start", "2000-01-01"),
        auto_update=bool(data_cfg.get("auto_update", True)),
    )
    if raw_df is None or raw_df.empty:
        print(f"??{ticker}: ?⊥?頛?∪鞈?")
        return None

    # 8) ?孵噩撱箸?
    from src.features.builder import build_features_for_ticker
    feature_df, _cache_key = build_features_for_ticker(
        cfg=pseudo_cfg,
        ticker=ticker,
        df_in=raw_df,
        benchmark_df=bm_df,
        use_cache=False,  # ?葫銝敹怠?嚗Ⅱ靽??迤蝣?
        include_labels=False,  # ?葫銝?閬?label嚗??瑕偏蝡航???
    )

    if not feature_cols:
        # fallback嚗 builder ?身
        from src.features.builder import DEFAULT_FEATURE_COLS
        feature_cols = list(DEFAULT_FEATURE_COLS)
        print(f"  ?? 雿輻 builder ?身 feature_cols ({len(feature_cols)} 甈?")

    # 蝘駁 feature NaN ????warmup ?嚗?皜砌??閬?label嚗?
    missing_cols = [c for c in feature_cols if c not in feature_df.columns]
    if missing_cols:
        print(f"  ?? 隞乩? feature_cols 銝 DataFrame 銝哨?撠蕭?? {missing_cols}")
        feature_cols = [c for c in feature_cols if c in feature_df.columns]

    pre_len = len(feature_df)
    feature_df = feature_df.dropna(subset=feature_cols)
    warmup_dropped = pre_len - len(feature_df)
    if warmup_dropped > 0:
        print(f"  ?對? feature warmup 蝘駁 {warmup_dropped} ??NaN (?拚? {len(feature_df)} ??")
    if len(feature_df) == 0:
        print(f"  ??feature dropna 敺鞈?")
        return None

    print(f"  ?對? 鞈?蝭?: {feature_df.index.min().strftime('%Y-%m-%d')} ~ {feature_df.index.max().strftime('%Y-%m-%d')}")

    # 9) ?瑁??葫
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
            print(f"  ?? Benchmark B&H 閮?憭望?: {e}")

    # 11) 撖怠?Ｙ
    out_dir.mkdir(parents=True, exist_ok=True)

    # config.yaml嚗??祕?????券閮剖?
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

    # end-date summary嚗??桃嚗?
    from src.backtest.io import save_end_date_summary
    eds_path = save_end_date_summary(
        result, bm_metrics, strategy, out_dir,
        start=bt_cfg["start"], end=bt_cfg["end"],
    )
    print(f"  ??頝??: {eds_path.as_posix()}")

    if do_plot:
        chart = plot_equity_curve(result, bm_metrics, bt_cfg, out_dir)
        if chart:
            print(f"  ??瘛典潭蝺? {chart.as_posix()}")

    # 12) stdout 蝮暹???
    m = result["metrics"]
    print(f"\n  ?? {ticker} 蝮暹?:")
    print(f"     蝮賢?? {m['total_return']*100:+.2f}%  CAGR: {m['cagr']*100:.2f}%")
    print(f"     MDD: {m['max_drawdown']*100:.2f}%  鈭斗?: {m['trade_count']}  ??: {m['win_rate']*100:.1f}%")
    print(f"     ???? {m['exposure_rate']*100:.1f}%  ??鈭斗?: {m['avg_trades_per_month']:.2f}")
    print(f"  ?? 頛詨: {out_dir.as_posix()}")

    return result


def _print_strategy_summary(strategy: dict) -> None:
    entry = strategy.get("entry", {})
    exit_s = strategy.get("exit", {})
    print("  蝑?:")
    for tier in entry.get("conf_thresholds", []):
        print(f"    靽∪?摨?>= {tier['min_conf']*100:.0f}% ??鞎瑕 {tier['buy_frac']*100:.0f}%")
    print(f"    撣瞈曄雯: {'ON' if entry.get('use_market_filter') else 'OFF'}")
    print(f"    ??: {exit_s.get('stop_loss_pct', 0)*100:.1f}%")
    print(f"    蝘餃????: {exit_s.get('take_profit_activation_pct', 0)*100:.1f}%")


# ??? CLI ??????????????????????????????????????????????????????????????

def main() -> None:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="Config-driven backtest runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", default="configs/backtest/base.yaml",
                        help="Backtest config path (default: configs/backtest/base.yaml)")
    parser.add_argument("--ticker", help="Single ticker (e.g. GOOGL)")
    parser.add_argument("--tickers", help="Comma-separated tickers (e.g. NVDA,GOOGL,TSM)")
    parser.add_argument("--start", help="Backtest start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="Backtest end date (YYYY-MM-DD)")
    parser.add_argument("--registry-best", default=None,
                        help="Path to registry_best_by_ticker.csv")
    parser.add_argument("--model-path", default=None,
                        help="Specify model file path directly (skip registry selection)")
    parser.add_argument("--mode", default=None, choices=["finetune", "base"],
                        help="Model mode (default: finetune)")
    parser.add_argument("--set", action="append", default=[],
                        help="Override config values with key=value")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate config and print summary without execution")
    parser.add_argument("--benchmark", default=None,
                        help="Benchmark symbol (default: ^IXIC)")
    plot_group = parser.add_mutually_exclusive_group()
    plot_group.add_argument("--plot", action="store_true", dest="plot", default=True)
    plot_group.add_argument("--no-plot", action="store_false", dest="plot")
    args = parser.parse_args()

    # 頛 config
    cfg = load_yaml(args.config)
    if args.set:
        cfg = apply_overrides(cfg, parse_set_values(args.set))

    # CLI 閬神?交?
    bt = cfg.setdefault("backtest", {})
    if args.start:
        bt["start"] = args.start
    if args.end:
        bt["end"] = args.end
    elif args.start and not args.end:
        # ?芰策 --start ??end = 隞予
        today_str = date.today().strftime("%Y-%m-%d")
        bt["end"] = today_str
        print(f"  ?對? end ?芣?摰???雿輻 today={today_str}")
    if args.benchmark:
        bt["benchmark"] = args.benchmark

    # 蝣箄??交?
    if "start" not in bt or "end" not in bt:
        print("[ERROR] backtest.start and backtest.end are required in config or CLI")
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
        print("???芣?摰?ticker?蝙??--ticker??-tickers ? config 銝剛身摰?backtest.tickers")
        sys.exit(1)

    print(f"\n?? ?葫??: {', '.join(tickers)}")
    print(f"   config: {args.config}")
    print(f"   ??: {bt['start']} ~ {bt['end']}")

    failed_tickers: list[str] = []

    for ticker in tickers:
        try:
            result = run_single_ticker(
                ticker,
                cfg,
                registry_rows=registry_rows,
                model_path_override=args.model_path,
                mode=mode,
                do_plot=args.plot,
                benchmark_symbol=benchmark_symbol,
                dry_run=args.dry_run,
            )
            if result is None and not args.dry_run:
                failed_tickers.append(ticker)
        except Exception as e:
            failed_tickers.append(ticker)
            print(f"??{ticker} ?葫憭望?: {e}")
            import traceback
            traceback.print_exc()

    if failed_tickers:
        failed_list = ', '.join(sorted(set(failed_tickers)))
        print(f"\n??Backtest failed for: {failed_list}")
        sys.exit(1)

    print("\n???葫摰?")

if __name__ == "__main__":
    main()





