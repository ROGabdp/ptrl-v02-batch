from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def _classification_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())

    total = max(1, len(y_true))
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / total
    return {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "support": int(len(y_true)),
    }


def evaluate_models_on_validation(
    feature_cols: list[str],
    val_data: dict[str, Any],
    ticker_model_paths: dict[str, str],
    threshold: float,
) -> dict[str, Any]:
    from stable_baselines3 import PPO

    per_ticker: dict[str, dict[str, float]] = {}
    y_all_true: list[np.ndarray] = []
    y_all_pred: list[np.ndarray] = []

    for ticker, df in val_data.items():
        model_path = ticker_model_paths.get(ticker)
        if not model_path or not Path(model_path).exists():
            continue
        model = PPO.load(model_path, device="cpu")
        x = df[feature_cols].values.astype(np.float32)
        y_true = (df["Next_Max_Return"].values >= threshold).astype(np.int8)
        preds = []
        for i in range(len(x)):
            action, _ = model.predict(x[i], deterministic=True)
            preds.append(int(action))
        y_pred = np.array(preds, dtype=np.int8)
        per_ticker[ticker] = _classification_metrics(y_true, y_pred)
        y_all_true.append(y_true)
        y_all_pred.append(y_pred)

    if not y_all_true:
        return {"overall": {}, "per_ticker": per_ticker}
    overall = _classification_metrics(np.concatenate(y_all_true), np.concatenate(y_all_pred))
    return {"overall": overall, "per_ticker": per_ticker}
