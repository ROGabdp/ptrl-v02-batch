"""Label Balance Finder — 搜尋使 positive_rate 接近目標比率的 (horizon, threshold) 組合。

用法：
    python -m scripts.find_label_balance --ticker NVDA --config configs/base.yaml
"""
from __future__ import annotations

import argparse
import csv
import re
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import load_yaml
from src.data.loader import load_or_update_local_csv
from src.labels.targets import add_buy_targets
from src.splits.time_split import filter_by_ranges, get_valid_train_ranges

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ─── add_buy_targets 產出的 label 欄位名（與 targets.py 嚴格對齊） ───
_LABEL_COL = "Label_Buy"
# 啟動時做一次 sanity check，確認 targets.py 確實產出此欄位
_SENTINEL_DF = pd.DataFrame({"Close": [100.0, 110.0, 120.0], "High": [105.0, 115.0, 125.0]})
_SENTINEL_OUT = add_buy_targets(_SENTINEL_DF, horizon_days=1, threshold=0.01)
if _LABEL_COL not in _SENTINEL_OUT.columns:
    # 若 targets.py 改名了，取最後一個新增的欄位
    _new_cols = [c for c in _SENTINEL_OUT.columns if c not in _SENTINEL_DF.columns]
    _candidates = [c for c in _new_cols if c != "Next_Max_Return"]
    if _candidates:
        _LABEL_COL = _candidates[-1]
        logger.warning("targets.py label 欄位名已變更，偵測到 '%s'", _LABEL_COL)
    else:
        raise RuntimeError("無法偵測 add_buy_targets 產出的 label 欄位")
del _SENTINEL_DF, _SENTINEL_OUT


# ─── 資料準備 ────────────────────────────────────────────────────────
def _load_ticker_data(cfg: dict[str, Any], ticker: str) -> pd.DataFrame:
    """載入單一 ticker 的原始 OHLCV 資料（與 training pipeline 相同來源）。"""
    data_root = cfg["data"]["data_root"]
    start_date = str(cfg["data"]["download_start"])
    auto_update = bool(cfg["data"].get("auto_update", True))
    df = load_or_update_local_csv(
        ticker=ticker,
        data_root=data_root,
        start_date=start_date,
        auto_update=auto_update,
    )
    if df is None or df.empty:
        raise RuntimeError(f"無法載入 ticker '{ticker}' 的資料")
    return df


def _split_train_val(
    cfg: dict[str, Any], df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """依 config 切出 train_df / val_df，並做排序、去重、重疊檢查。"""
    warmup = int(cfg["splits"]["warmup_days"])
    train_ranges = cfg["splits"]["train_ranges"]
    val_start, val_end = cfg["splits"]["val_range"]

    # train：合併多段區間
    valid_ranges = get_valid_train_ranges(df, train_ranges, warmup)
    if not valid_ranges:
        raise RuntimeError("warmup 後無有效 train 區間")
    train_df = filter_by_ranges(df, valid_ranges)
    train_df = train_df.sort_index()
    train_df = train_df[~train_df.index.duplicated(keep="last")]

    # val
    val_df = df[(df.index >= pd.Timestamp(val_start)) & (df.index <= pd.Timestamp(val_end))]
    val_df = val_df.sort_index()
    val_df = val_df[~val_df.index.duplicated(keep="last")]

    # 重疊檢查
    overlap = train_df.index.intersection(val_df.index)
    if len(overlap) > 0:
        logger.warning(
            "train/val 有 %d 筆重疊日期（%s ~ %s），已從 train 移除",
            len(overlap),
            overlap.min().strftime("%Y-%m-%d"),
            overlap.max().strftime("%Y-%m-%d"),
        )
        train_df = train_df.drop(overlap)

    return train_df, val_df


# ─── 排序邏輯 ─────────────────────────────────────────────────────────
def _sort_key_both(row: dict, target_rate: float) -> tuple:
    """四重排序：delta_val → delta_train → gap → -N（both 模式）。"""
    return (
        row["delta_val"],        # 1. 最小化 |val_positive_rate - target_rate|
        row["delta_train"],      # 2. 最小化 |train_positive_rate - target_rate|
        row["gap_train_val"],    # 3. 最小化 |train - val|
        -(row["N_val"] + row["N_train"]),  # 4. 樣本越多越好（取反）
    )


def _sort_key_val(row: dict, target_rate: float) -> tuple:
    """val 模式：只看 delta_val → -N_val。"""
    return (row["delta_val"], -row["N_val"])


def _sort_key_train(row: dict, target_rate: float) -> tuple:
    """train 模式：只看 delta_train → -N_train。"""
    return (row["delta_train"], -row["N_train"])


_SORT_FN = {
    "both": _sort_key_both,
    "val": _sort_key_val,
    "train": _sort_key_train,
}


# ─── 核心計算 ─────────────────────────────────────────────────────────
def _compute_one(
    raw_df: pd.DataFrame,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    horizon: int,
    threshold: float,
    future_price_field: str,
    include_today: bool,
    target_rate: float,
    split_mode: str,
) -> dict:
    """對單一 (horizon, threshold) 組合計算 positive_rate 等指標。"""

    result: dict[str, Any] = {
        "horizon_days": horizon,
        "target_return": threshold,
    }

    for name, sub_df in [("train", train_df), ("val", val_df)]:
        if split_mode != "both" and split_mode != name:
            # 單邊模式只算指定的 split
            result[f"{name}_positive_rate"] = float("nan")
            result[f"N_{name}"] = 0
            result[f"{name}_date_range"] = ""
            continue

        labeled = add_buy_targets(
            sub_df, horizon_days=horizon, threshold=threshold,
            future_price_field=future_price_field, include_today=include_today,
        )
        valid = labeled[_LABEL_COL].dropna()
        n = len(valid)
        rate = float(valid.mean()) if n > 0 else float("nan")

        result[f"{name}_positive_rate"] = rate
        result[f"N_{name}"] = n
        if n > 0:
            result[f"{name}_date_range"] = (
                f"{valid.index.min().strftime('%Y-%m-%d')} ~ "
                f"{valid.index.max().strftime('%Y-%m-%d')}"
            )
        else:
            result[f"{name}_date_range"] = ""

    # delta / gap
    vr = result.get("val_positive_rate", float("nan"))
    tr = result.get("train_positive_rate", float("nan"))
    result["delta_val"] = abs(vr - target_rate) if pd.notna(vr) else float("inf")
    result["delta_train"] = abs(tr - target_rate) if pd.notna(tr) else float("inf")
    result["gap_train_val"] = (
        abs(tr - vr) if pd.notna(tr) and pd.notna(vr) else float("inf")
    )

    return result


# ─── 主程式 ───────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="搜尋使 positive_rate ≈ target_rate 的 (horizon, threshold) 組合",
    )
    parser.add_argument("--ticker", required=True, help="必填，單一 ticker（如 NVDA）")
    parser.add_argument("--config", default="configs/base.yaml", help="config 路徑")
    parser.add_argument("--horizons", default="10,20,40", help="逗號分隔整數")
    parser.add_argument("--returns", default="0.05,0.10,0.15", help="逗號分隔浮點")
    parser.add_argument("--target-rate", type=float, default=0.5, help="目標 positive_rate")
    parser.add_argument("--top-k", type=int, default=10, help="顯示前 k 名")
    parser.add_argument("--out", default=None, help="輸出路徑 (.csv/.json)")
    parser.add_argument("--save", action="store_true", help="自動產生檔名並輸出到 reports/label_balance/")
    parser.add_argument(
        "--format", default="csv", choices=["csv", "json"],
        dest="fmt", help="輸出格式（預設 csv，搭配 --save 使用）",
    )
    parser.add_argument("--dry-run", action="store_true", help="只印出評估組合與資料概要")
    parser.add_argument(
        "--split", default="both", choices=["val", "train", "both"],
        help="計算哪個 split（預設 both）",
    )

    args = parser.parse_args(argv)

    # ── 解析 horizons / returns ──
    horizons = [int(x.strip()) for x in args.horizons.split(",")]
    returns = [float(x.strip()) for x in args.returns.split(",")]
    ticker: str = args.ticker.upper()
    target_rate: float = args.target_rate
    top_k: int = args.top_k
    split_mode: str = args.split

    # ── 載入 config ──
    cfg = load_yaml(args.config)
    future_price_field: str = cfg["label"].get("future_price_field", "High")
    include_today: bool = bool(cfg["label"].get("include_today", False))

    # ── 載入資料 & 切分 ──
    logger.info("載入 %s 的原始資料…", ticker)
    raw_df = _load_ticker_data(cfg, ticker)
    train_df, val_df = _split_train_val(cfg, raw_df)

    grid_size = len(horizons) * len(returns)

    # ── dry-run ──
    if args.dry_run:
        print(f"\n{'='*60}")
        print(f"  Label Balance Finder — Dry Run")
        print(f"{'='*60}")
        print(f"  Ticker        : {ticker}")
        print(f"  Config        : {args.config}")
        print(f"  Target Rate   : {target_rate}")
        print(f"  Split Mode    : {split_mode}")
        print(f"  Horizons      : {horizons}")
        print(f"  Returns       : {returns}")
        print(f"  Grid Size     : {grid_size} 組合")
        print(f"  Top-K         : {top_k}")
        print()
        print(f"  Train  N      : {len(train_df)}")
        if len(train_df) > 0:
            print(f"  Train  Range  : {train_df.index.min().strftime('%Y-%m-%d')} ~ "
                  f"{train_df.index.max().strftime('%Y-%m-%d')}")
        print(f"  Val    N      : {len(val_df)}")
        if len(val_df) > 0:
            print(f"  Val    Range  : {val_df.index.min().strftime('%Y-%m-%d')} ~ "
                  f"{val_df.index.max().strftime('%Y-%m-%d')}")
        print(f"{'='*60}\n")
        return

    # ── 計算每個組合 ──
    logger.info("開始計算 %d 個 (horizon, threshold) 組合…", grid_size)
    results: list[dict] = []
    for h in horizons:
        for r in returns:
            row = _compute_one(
                raw_df, train_df, val_df,
                horizon=h, threshold=r,
                future_price_field=future_price_field,
                include_today=include_today,
                target_rate=target_rate,
                split_mode=split_mode,
            )
            results.append(row)

    # ── 排序 ──
    sort_fn = _SORT_FN[split_mode]
    results.sort(key=lambda row: sort_fn(row, target_rate))

    top_results = results[:top_k]

    # ── 印出 stdout 表格 ──
    _print_table(top_results, split_mode)

    # ── 寫檔 ──
    # 優先順序：--out 顯式路徑 > --save 自動產生檔名
    if args.out:
        _save_output(args.out, ticker, split_mode, results)
    elif args.save:
        auto_name = _auto_filename(
            ticker=ticker,
            split_mode=split_mode,
            horizons=horizons,
            returns_list=returns,
            target_rate=target_rate,
            config_path=args.config,
            fmt=args.fmt,
        )
        _save_output(auto_name, ticker, split_mode, results)


# ─── 格式化輸出 ───────────────────────────────────────────────────────
_TABLE_COLS_BOTH = [
    "rank", "horizon_days", "target_return",
    "val_positive_rate", "train_positive_rate", "gap_train_val",
    "N_val", "N_train",
    "val_date_range", "train_date_range",
]

_TABLE_COLS_VAL = [
    "rank", "horizon_days", "target_return",
    "val_positive_rate", "delta_val", "N_val", "val_date_range",
]

_TABLE_COLS_TRAIN = [
    "rank", "horizon_days", "target_return",
    "train_positive_rate", "delta_train", "N_train", "train_date_range",
]


def _print_table(rows: list[dict], split_mode: str) -> None:
    if not rows:
        print("（無結果）")
        return

    if split_mode == "both":
        cols = _TABLE_COLS_BOTH
    elif split_mode == "val":
        cols = _TABLE_COLS_VAL
    else:
        cols = _TABLE_COLS_TRAIN

    # 準備可印出的字串行
    header = cols
    str_rows: list[list[str]] = []
    for i, row in enumerate(rows, 1):
        cells: list[str] = []
        for c in cols:
            if c == "rank":
                cells.append(str(i))
            elif c in ("val_positive_rate", "train_positive_rate", "gap_train_val",
                        "delta_val", "delta_train"):
                v = row.get(c, float("nan"))
                cells.append(f"{v:.4f}" if pd.notna(v) and v != float("inf") else "N/A")
            elif c in ("target_return",):
                cells.append(f"{row[c]:.4f}")
            elif c in ("N_val", "N_train", "horizon_days"):
                cells.append(str(row.get(c, 0)))
            else:
                cells.append(str(row.get(c, "")))
        str_rows.append(cells)

    # 計算欄寬
    widths = [len(h) for h in header]
    for sr in str_rows:
        for j, cell in enumerate(sr):
            widths[j] = max(widths[j], len(cell))

    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    fmt = "| " + " | ".join(f"{{:<{w}}}" for w in widths) + " |"

    print()
    print(sep)
    print(fmt.format(*header))
    print(sep)
    for sr in str_rows:
        print(fmt.format(*sr))
    print(sep)
    print()


# ─── 自動檔名產生 ──────────────────────────────────────────────────────
_DEFAULT_OUT_DIR = Path("reports/label_balance")


def _auto_filename(
    ticker: str,
    split_mode: str,
    horizons: list[int],
    returns_list: list[float],
    target_rate: float,
    config_path: str,
    fmt: str = "csv",
) -> str:
    """根據 CLI 參數自動產生可讀、可辨識的檔名。

    格式：
      label_balance__{TICKER}__{split}__H{horizons}__R{returns}__TR{rate}__CFG{base}__{ts}.{ext}
    """
    h_part = "-".join(str(h) for h in horizons)
    r_part = "-".join(f"{r:.2f}" for r in returns_list)
    tr_part = f"{target_rate:.2f}"
    cfg_base = Path(config_path).stem          # e.g. "base"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = fmt if fmt in ("csv", "json") else "csv"

    name = (
        f"label_balance__{ticker}__{split_mode}"
        f"__H{h_part}__R{r_part}__TR{tr_part}"
        f"__CFG{cfg_base}__{ts}.{ext}"
    )
    # 安全化：移除 Windows 不允許的字元（空白、冒號、引號等）
    name = re.sub(r'[\s:"<>|?*]', '_', name)
    return str(_DEFAULT_OUT_DIR / name)


# ─── 檔案輸出 ─────────────────────────────────────────────────────────


def _resolve_out_path(out_arg: str, ticker: str, split_mode: str) -> Path:
    """解析 --out 路徑，套用預設目錄與禁止 runs/ 規則。"""
    p = Path(out_arg)

    # 嚴禁輸出到 runs/
    resolved = p.resolve()
    if "runs" in resolved.parts:
        raise ValueError(f"嚴禁輸出到 runs/ 目錄：{p}")

    # 若路徑不含目錄部分（只有檔名），放到預設目錄
    if p.parent == Path(".") or str(p.parent) == ".":
        p = _DEFAULT_OUT_DIR / p

    return p


def _save_output(
    out_arg: str, ticker: str, split_mode: str, results: list[dict]
) -> None:
    out_path = _resolve_out_path(out_arg, ticker, split_mode)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    suffix = out_path.suffix.lower()
    if suffix == ".json":
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    elif suffix == ".csv":
        if results:
            keys = results[0].keys()
            with out_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(results)
    else:
        # 預設 CSV
        out_path = out_path.with_suffix(".csv")
        if results:
            keys = results[0].keys()
            with out_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(results)

    logger.info("結果已寫入 %s", out_path)


# ─── Entry point ──────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
