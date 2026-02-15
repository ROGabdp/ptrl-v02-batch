"""Model Registry CLI — 掃描 runs/ 建立模型索引並產生 best-by-ticker 摘要。

用法：
    python -m scripts.index_runs --runs-dir runs --out-dir reports/registry
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

from src.registry.indexer import (
    _MODEL_ROW_KEYS,
    save_csv,
    save_json,
    scan_all_runs,
    select_best_by_ticker,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="掃描 runs/ 建立模型索引與 best-by-ticker 摘要",
    )
    parser.add_argument("--runs-dir", default="runs", help="runs 根目錄（預設 runs）")
    parser.add_argument("--out-dir", default="reports/registry", help="輸出目錄（預設 reports/registry）")
    parser.add_argument("--buy-rate-max", type=float, default=None, help="best_by_ticker 過濾：buy_rate 上限（預設不啟用）")
    parser.add_argument("--lift-min", type=float, default=1.10, help="best_by_ticker 過濾：lift 下限（預設 1.10）")
    parser.add_argument("--include-incomplete", action="store_true", help="包含缺檔的 run")
    parser.add_argument(
        "--format", default="both", choices=["csv", "json", "both"],
        dest="fmt", help="輸出格式（預設 both）",
    )
    parser.add_argument(
        "--sort-preset", default="precision_first",
        choices=["precision_first", "lift_first"],
        help="best_by_ticker 排序規則（預設 precision_first）",
    )
    parser.add_argument("--min-tp", type=int, default=30, help="best_by_ticker 過濾：tp 下限（預設 30）")
    parser.add_argument("--min-positive-rate", type=float, default=None, help="best_by_ticker 過濾：positive_rate 下限（選填）")
    parser.add_argument("--quiet", action="store_true", help="減少輸出")

    args = parser.parse_args(argv)
    runs_dir = Path(args.runs_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.quiet:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)

    # ── 掃描 ──
    rows = scan_all_runs(runs_dir, include_incomplete=args.include_incomplete)
    logger.info("registry_models 共 %d 列", len(rows))

    # ── best_by_ticker ──
    best = select_best_by_ticker(
        rows,
        buy_rate_max=args.buy_rate_max,
        lift_min=args.lift_min,
        sort_preset=args.sort_preset,
        min_tp=args.min_tp,
        min_positive_rate=args.min_positive_rate,
    )

    # ── 輸出 ──
    now_str = datetime.now().isoformat()
    metadata = {
        "generated_at": now_str,
        "runs_dir": str(runs_dir.resolve()),
        "buy_rate_max": args.buy_rate_max,
        "lift_min": args.lift_min,
        "sort_preset": args.sort_preset,
        "min_tp": args.min_tp,
        "min_positive_rate": args.min_positive_rate,
        "include_incomplete": args.include_incomplete,
        "total_rows": len(rows),
        "total_best": len(best),
    }

    written: list[str] = []
    fmt = args.fmt

    if fmt in ("csv", "both"):
        p1 = out_dir / "registry_models.csv"
        n1 = save_csv(rows, p1, fieldnames=_MODEL_ROW_KEYS)
        written.append(f"  {p1}  ({n1} 列)")

        best_keys = _MODEL_ROW_KEYS + ["best_status", "selection_sort_key", "selection_filters"]
        p2 = out_dir / "registry_best_by_ticker.csv"
        n2 = save_csv(best, p2, fieldnames=best_keys)
        written.append(f"  {p2}  ({n2} 列)")

    if fmt in ("json", "both"):
        p3 = out_dir / "registry_models.json"
        n3 = save_json(rows, p3, metadata=metadata)
        written.append(f"  {p3}  ({n3} 列)")

        p4 = out_dir / "registry_best_by_ticker.json"
        n4 = save_json(best, p4, metadata=metadata)
        written.append(f"  {p4}  ({n4} 列)")

    # ── stdout 摘要 ──
    print(f"\n{'='*70}")
    print(f"  Model Registry — 索引完成")
    print(f"{'='*70}")
    print(f"  掃描目錄      : {runs_dir.resolve()}")
    print(f"  registry 列數 : {len(rows)}")
    print(f"  best_by_ticker: {len(best)} tickers")
    print(f"  排序規則      : {args.sort_preset}")
    _br = f"<= {args.buy_rate_max}" if args.buy_rate_max is not None else "不限"
    print(f"  過濾門檻      : lift >= {args.lift_min}, tp >= {args.min_tp}, buy_rate {_br}")
    if args.min_positive_rate is not None:
        print(f"                  min_positive_rate >= {args.min_positive_rate}")
    print()
    print("  輸出檔案：")
    for w in written:
        print(w)
    print()

    # ── best_by_ticker 摘要表 ──
    if best:
        print(f"  {'─'*66}")
        print(f"  Best by Ticker:")
        print(f"  {'─'*66}")
        header = f"  {'ticker':<8} {'status':<32} {'prec':>6} {'lift':>6} {'buy_r':>6} {'tp':>5} {'horiz':>5} {'thresh':>6} model_path"
        print(header)
        print(f"  {'─'*110}")
        for b in best:
            lift_s = f"{b['lift']:.3f}" if b.get("lift") is not None else "N/A"
            prec_s = f"{b['precision']:.3f}" if b.get("precision") is not None else "N/A"
            buyr_s = f"{b['buy_rate']:.3f}" if b.get("buy_rate") is not None else "N/A"
            tp_s = str(b.get("tp", "?"))
            horiz_s = str(b.get("label_horizon_days", "?"))
            thresh_s = f"{b['label_threshold']:.2f}" if b.get("label_threshold") is not None else "?"
            model_s = b.get("model_final_path", "N/A") or "N/A"
            bs = b.get("best_status", "?")
            print(f"  {b['ticker']:<8} {bs:<32} {prec_s:>6} {lift_s:>6} {buyr_s:>6} {tp_s:>5} {horiz_s:>5} {thresh_s:>6} {model_s}")
        print(f"  {'─'*110}")
    else:
        print("  （無 best_by_ticker 結果）")

    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
