"""模型選擇 — 從 registry 或手動路徑取得 ticker 模型與訓練設定。"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from src.config import load_yaml


# ─── Registry 讀取 ────────────────────────────────────────────────────

def load_registry_best(csv_path: str | Path) -> list[dict]:
    """讀取 registry_best_by_ticker.csv，回傳 list[dict]。"""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Registry CSV not found: {path}")
    with path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def _find_registry_row(
    ticker: str,
    rows: list[dict],
    mode: str = "finetune",
) -> dict | None:
    """在 registry rows 中找到 ticker + mode 匹配的列。"""
    for r in rows:
        if r.get("ticker", "").upper() == ticker.upper() and r.get("mode", "") == mode:
            return r
    return None


# ─── 訓練設定讀取 ─────────────────────────────────────────────────────

def _training_config_from_registry(row: dict) -> dict[str, Any] | None:
    """從 registry row 的 config_path 讀取訓練 config，確保特徵一致。"""
    config_path = row.get("config_path", "")
    if not config_path:
        return None
    p = Path(config_path)
    if not p.exists():
        return None
    try:
        return load_yaml(p)
    except Exception:
        return None


# ─── 公開 API ─────────────────────────────────────────────────────────

def select_model_for_ticker(
    ticker: str,
    *,
    registry_rows: list[dict] | None = None,
    mode: str = "finetune",
    model_path_override: str | None = None,
) -> dict[str, Any]:
    """為指定 ticker 選模型。

    回傳 dict 包含：
      model_path, label_horizon_days, label_threshold,
      registry_row (原始 dict 或 None), train_cfg (訓練 config 或 None)
    """
    result: dict[str, Any] = {
        "ticker": ticker,
        "model_path": None,
        "label_horizon_days": None,
        "label_threshold": None,
        "registry_row": None,
        "train_cfg": None,
    }

    # 強制覆寫路徑
    if model_path_override:
        result["model_path"] = model_path_override
        return result

    # Registry 查詢
    if registry_rows is None:
        raise ValueError("No registry rows and no model_path_override provided")

    row = _find_registry_row(ticker, registry_rows, mode)
    if row is None:
        raise ValueError(
            f"Ticker '{ticker}' (mode={mode}) not found in registry. "
            f"Available: {[r.get('ticker') for r in registry_rows]}"
        )

    result["model_path"] = row.get("model_final_path")
    result["registry_row"] = row
    try:
        result["label_horizon_days"] = int(row["label_horizon_days"])
    except (KeyError, ValueError, TypeError):
        pass
    try:
        result["label_threshold"] = float(row["label_threshold"])
    except (KeyError, ValueError, TypeError):
        pass

    # 讀取訓練 config 以確保特徵一致
    result["train_cfg"] = _training_config_from_registry(row)
    return result
