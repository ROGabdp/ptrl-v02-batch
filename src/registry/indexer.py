"""Registry indexer — 掃描 runs/ 產生模型索引與 best-by-ticker 摘要。

核心流程：
1. 掃描 runs/<run_id>/ 下的 manifest.json / config.yaml / metrics.json
2. 展開為「每個 ticker-model」一列（base / finetune）
3. 計算 lift = precision / positive_rate
4. 依選模規則產生 best_by_ticker 摘要
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


# ─── 欄位定義 ─────────────────────────────────────────────────────────
_MODEL_ROW_KEYS = [
    "run_id", "mode", "ticker",
    "label_horizon_days", "label_threshold",
    "precision", "recall", "f1", "accuracy",
    "buy_rate", "positive_rate", "lift",
    "tp", "fp", "tn", "fn", "support",
    "model_final_path",
    "config_path", "metrics_path", "manifest_path",
    "git_commit", "start_time", "end_time",
    "status",
]


# ─── 掃描單一 run ─────────────────────────────────────────────────────
def _read_json(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _read_yaml(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return None


def _model_status(model_path: str | None, run_dir: Path) -> str:
    """判斷模型狀態：READY / NO_FINAL / MISSING_MODEL。"""
    if not model_path:
        return "MISSING_MODEL"
    p = Path(model_path)
    if not p.is_absolute():
        p = run_dir.parent.parent / p  # runs_root 相對路徑
    if p.exists():
        return "READY"
    # 檢查同目錄是否有 best.zip / last.zip
    parent = p.parent
    if parent.exists() and any((parent / n).exists() for n in ("best.zip", "last.zip")):
        return "NO_FINAL"
    return "MISSING_MODEL"


def _make_row(
    run_id: str,
    mode: str,
    ticker: str,
    model_path: str | None,
    label_cfg: dict,
    metrics: dict | None,
    manifest: dict,
    run_dir: Path,
) -> dict:
    """組成一列 registry row。"""
    row: dict[str, Any] = {
        "run_id": run_id,
        "mode": mode,
        "ticker": ticker,
        "label_horizon_days": label_cfg.get("horizon_days"),
        "label_threshold": label_cfg.get("threshold"),
    }

    # metrics
    if metrics:
        for k in ("precision", "recall", "f1", "accuracy",
                   "buy_rate", "positive_rate",
                   "tp", "fp", "tn", "fn", "support"):
            row[k] = metrics.get(k)
        pr = metrics.get("positive_rate")
        prec = metrics.get("precision")
        if pr and pr > 0 and prec is not None:
            row["lift"] = round(prec / pr, 6)
        else:
            row["lift"] = None
    else:
        for k in ("precision", "recall", "f1", "accuracy",
                   "buy_rate", "positive_rate", "lift",
                   "tp", "fp", "tn", "fn", "support"):
            row[k] = None

    row["model_final_path"] = model_path
    row["config_path"] = str(run_dir / "config.yaml")
    row["metrics_path"] = str(run_dir / "metrics.json")
    row["manifest_path"] = str(run_dir / "manifest.json")
    row["git_commit"] = manifest.get("git_commit")
    row["start_time"] = manifest.get("start_time")
    row["end_time"] = manifest.get("end_time")

    # 模型路徑相對於 repo root（runs_dir 的 parent）
    row["status"] = _model_status(model_path, run_dir)

    return row


def scan_single_run(run_dir: Path, include_incomplete: bool = False) -> list[dict]:
    """掃描單一 run 目錄，回傳展開的 registry rows。"""
    rows: list[dict] = []
    run_id = run_dir.name

    manifest = _read_json(run_dir / "manifest.json")
    cfg = _read_yaml(run_dir / "config.yaml")
    metrics_data = _read_json(run_dir / "metrics.json")

    if manifest is None:
        if include_incomplete:
            rows.append({k: None for k in _MODEL_ROW_KEYS})
            rows[-1].update(run_id=run_id, status="MISSING_MANIFEST")
        return rows

    label_cfg = (cfg or {}).get("label", {})
    per_ticker_metrics = (metrics_data or {}).get("per_ticker", {})

    # ── finetune models ──
    ticker_paths = manifest.get("per_ticker_final_paths", {})
    for ticker, model_path in ticker_paths.items():
        ticker_metrics = per_ticker_metrics.get(ticker)
        if ticker_metrics is None and not include_incomplete:
            continue
        row = _make_row(
            run_id=run_id, mode="finetune", ticker=ticker,
            model_path=model_path, label_cfg=label_cfg,
            metrics=ticker_metrics, manifest=manifest, run_dir=run_dir,
        )
        if ticker_metrics is None:
            row["status"] = "MISSING_METRICS"
        rows.append(row)

    # ── base model ──
    base_path = manifest.get("base_final_path")
    if base_path:
        # base 用 overall metrics
        overall_metrics = (metrics_data or {}).get("overall")
        if overall_metrics is not None or include_incomplete:
            row = _make_row(
                run_id=run_id, mode="base", ticker="ALL",
                model_path=base_path, label_cfg=label_cfg,
                metrics=overall_metrics, manifest=manifest, run_dir=run_dir,
            )
            if overall_metrics is None:
                row["status"] = "MISSING_METRICS"
            rows.append(row)

    return rows


# ─── 掃描整個 runs/ ───────────────────────────────────────────────────
def scan_all_runs(
    runs_dir: Path, include_incomplete: bool = False
) -> list[dict]:
    """掃描 runs_dir 下所有 run 目錄，回傳完整 registry rows。"""
    rows: list[dict] = []
    if not runs_dir.exists():
        logger.warning("runs 目錄不存在：%s", runs_dir)
        return rows

    run_dirs = sorted(
        [d for d in runs_dir.iterdir() if d.is_dir()],
        key=lambda d: d.name,
    )
    logger.info("掃描到 %d 個 run 目錄", len(run_dirs))

    for rd in run_dirs:
        try:
            sub = scan_single_run(rd, include_incomplete=include_incomplete)
            rows.extend(sub)
        except Exception as e:
            logger.error("掃描 %s 失敗：%s", rd.name, e)
            if include_incomplete:
                rows.append({
                    k: None for k in _MODEL_ROW_KEYS
                })
                rows[-1].update(run_id=rd.name, status=f"ERROR: {e}")

    return rows


# ─── 排序 presets ──────────────────────────────────────────────────────
def _sort_key_precision_first(r: dict) -> tuple:
    """precision ↓ → lift ↓ → buy_rate ↑ → support ↓"""
    return (
        -(r.get("precision") or 0),
        -(r.get("lift") or 0),
        (r.get("buy_rate") or 1),
        -(r.get("support") or 0),
    )


def _sort_key_lift_first(r: dict) -> tuple:
    """lift ↓ → precision ↓ → buy_rate ↑ → support ↓"""
    return (
        -(r.get("lift") or 0),
        -(r.get("precision") or 0),
        (r.get("buy_rate") or 1),
        -(r.get("support") or 0),
    )


_SORT_PRESETS = {
    "precision_first": _sort_key_precision_first,
    "lift_first": _sort_key_lift_first,
}


def _format_sort_key(r: dict) -> str:
    """產生可讀的排序 key 字串，方便驗證。"""
    prec = f"{r.get('precision', 0):.3f}" if r.get("precision") is not None else "N/A"
    lift = f"{r.get('lift', 0):.3f}" if r.get("lift") is not None else "N/A"
    buyr = f"{r.get('buy_rate', 0):.3f}" if r.get("buy_rate") is not None else "N/A"
    supp = str(r.get("support", 0))
    tp = str(r.get("tp", 0))
    return f"precision={prec}|lift={lift}|buy_rate={buyr}|support={supp}|tp={tp}"


def _format_filters(
    lift_min: float,
    min_tp: int,
    buy_rate_max: float | None,
    min_positive_rate: float | None,
) -> str:
    """產生門檻摘要字串。"""
    parts = [f"lift_min={lift_min}", f"min_tp={min_tp}"]
    parts.append(f"buy_rate_max={buy_rate_max}" if buy_rate_max is not None else "buy_rate_max=None")
    if min_positive_rate is not None:
        parts.append(f"min_positive_rate={min_positive_rate}")
    return "; ".join(parts)


# ─── best_by_ticker ────────────────────────────────────────────────────
def select_best_by_ticker(
    rows: list[dict],
    buy_rate_max: float | None = None,
    lift_min: float = 1.10,
    sort_preset: str = "precision_first",
    min_tp: int = 30,
    min_positive_rate: float | None = None,
) -> list[dict]:
    """依選模規則為每個 ticker 選出最佳模型。

    過濾條件（全部需通過）：
      - lift >= lift_min（預設 1.05，確保比亂買好）
      - tp >= min_tp（預設 30，避免事件太稀有造成假象）
      - buy_rate <= buy_rate_max（僅在明確指定時啟用）
      - positive_rate >= min_positive_rate（僅在明確指定時啟用）

    排序 presets：
      - precision_first：precision ↓ → lift ↓ → buy_rate ↑ → support ↓（預設）
      - lift_first：lift ↓ → precision ↓ → buy_rate ↑ → support ↓

    若無模型通過過濾，放寬至 lift >= 1.0 且 tp >= 1，標記 best_status="NO_PASS: <reason>"
    """
    sort_fn = _SORT_PRESETS.get(sort_preset, _sort_key_precision_first)
    filters_str = _format_filters(lift_min, min_tp, buy_rate_max, min_positive_rate)

    # 只考慮有完整 metrics 與有效模型的列
    valid = [
        r for r in rows
        if r.get("lift") is not None
        and r.get("precision") is not None
        and r.get("status") in ("READY", "NO_FINAL")
    ]

    # 依 ticker 分組（排除 base 的 "ALL"）
    by_ticker: dict[str, list[dict]] = {}
    for r in valid:
        t = r["ticker"]
        if t == "ALL":
            continue
        by_ticker.setdefault(t, []).append(r)

    def _passes_filters(c: dict) -> tuple[bool, str]:
        """檢查是否通過所有門檻，回傳 (pass, reason)。"""
        reasons: list[str] = []
        if (c.get("lift") or 0) < lift_min:
            reasons.append(f"lift<{lift_min}")
        if (c.get("tp") or 0) < min_tp:
            reasons.append(f"tp<{min_tp}")
        if buy_rate_max is not None and (c.get("buy_rate") or 1) > buy_rate_max:
            reasons.append(f"buy_rate>{buy_rate_max}")
        if min_positive_rate is not None and (c.get("positive_rate") or 0) < min_positive_rate:
            reasons.append(f"positive_rate<{min_positive_rate}")
        return (len(reasons) == 0, "; ".join(reasons))

    best: list[dict] = []
    for ticker, candidates in sorted(by_ticker.items()):
        # 先嘗試嚴格過濾
        passed = [c for c in candidates if _passes_filters(c)[0]]
        if passed:
            passed.sort(key=sort_fn)
            entry = dict(passed[0])
            entry["best_status"] = "PASS"
        else:
            # 放寬至 lift >= 1.0 且 tp >= 1
            relaxed = [
                c for c in candidates
                if (c.get("lift") or 0) >= 1.0
                and (c.get("tp") or 0) >= 1
            ]
            if relaxed:
                relaxed.sort(key=sort_fn)
                entry = dict(relaxed[0])
            else:
                # 全無符合，選排序最優的
                candidates.sort(key=sort_fn)
                entry = dict(candidates[0])
            _, reason = _passes_filters(entry)
            entry["best_status"] = f"NO_PASS: {reason}" if reason else "NO_PASS"

        entry["selection_sort_key"] = _format_sort_key(entry)
        entry["selection_filters"] = filters_str
        best.append(entry)

    return best



# ─── 存檔 ─────────────────────────────────────────────────────────────
def save_csv(rows: list[dict], path: Path, fieldnames: list[str] | None = None) -> int:
    """寫 CSV，回傳列數。"""
    import csv
    if not rows:
        path.write_text("", encoding="utf-8")
        return 0
    keys = fieldnames or list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def save_json(
    rows: list[dict],
    path: Path,
    *,
    metadata: dict | None = None,
) -> int:
    """寫 JSON，回傳列數。"""
    output: dict[str, Any] = {}
    if metadata:
        output["metadata"] = metadata
    output["data"] = rows
    with path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    return len(rows)
