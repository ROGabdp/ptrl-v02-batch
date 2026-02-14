from __future__ import annotations
import argparse
import json
import logging
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
from stable_baselines3 import PPO
from src.config import load_yaml
from src.data.loader import fetch_all_stock_data
from src.features.builder import build_all_features
from src.eval.metrics import _classification_metrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def evaluate_run(
    run_dir: Path,
    config_path: Path | None = None,
    model_path: Path | None = None,
    mode: str = "finetune",
) -> None:
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    # 1. Load Config
    if config_path:
        cfg = load_yaml(config_path)
    else:
        cfg_path = run_dir / "config.yaml"
        if not cfg_path.exists():
             # Fallback to local config if valid
             local_cfg = Path("configs/base.yaml")
             if local_cfg.exists():
                 logger.warning(f"Config not found in run_dir, using local {local_cfg}")
                 cfg = load_yaml(local_cfg)
             else:
                 raise FileNotFoundError(f"Config not found in {run_dir} and no override provided")
        else:
            cfg = load_yaml(cfg_path)

    # 2. Load Data & Features
    logger.info("Loading data...")
    raw_data = fetch_all_stock_data(cfg)
    feature_data, _ = build_all_features(cfg, raw_data, use_cache=True)
    
    # Filter for validation period
    val_start, val_end = cfg["splits"]["val_range"]
    val_data = {}
    for ticker, df in feature_data.items():
        mask = (df.index >= val_start) & (df.index <= val_end)
        val_data[ticker] = df[mask].copy()

    feature_cols = cfg["features"]["feature_cols"]
    threshold = float(cfg["label"]["threshold"])

    # 3. Predict & Evaluate
    per_ticker = {}
    y_all_true = []
    y_all_pred = []
    
    target_tickers = cfg["universe"]["tickers"]
    if mode == "finetune":
        # Specific tickers mentioned in finetune config or all universe
        # Usually we evaluate on all universe tickers if possible, 
        # but logically finetune mode implies per-ticker models.
        # If a ticker has no finetuned model, we skip or warn.
        pass

    logger.info(f"Evaluating in mode: {mode}")

    for ticker in target_tickers:
        if ticker not in val_data:
            continue
            
        df = val_data[ticker]
        if len(df) == 0:
            continue

        # Feature columns -> X
        # Missing columns check
        missing = [c for c in feature_cols if c not in df.columns]
        if missing:
            logger.warning(f"Ticker {ticker} missing features: {missing}, skipping")
            continue
            
        X = df[feature_cols].values.astype(np.float32)
        
        # Label generation (consistent with targets.py / metrics.py plan)
        # We rely on Next_Max_Return which should exist from builder
        if "Next_Max_Return" not in df.columns:
             logger.warning(f"Ticker {ticker} missing Next_Max_Return, skipping")
             continue
             
        y_true = (df["Next_Max_Return"].values >= threshold).astype(np.int8)

        # Resolve Model Path
        current_model_path = None
        if model_path:
            current_model_path = model_path
        elif mode == "finetune":
            # runs/<run_id>/models/finetuned/<TICKER>/{final, best, last}.zip
            model_dir = run_dir / "models" / "finetuned" / ticker
            for name in ["final.zip", "best.zip", "last.zip"]:
                p = model_dir / name
                if p.exists():
                    current_model_path = p
                    break
        elif mode == "base":
             # runs/<run_id>/models/base/{final, best, last}.zip
            model_dir = run_dir / "models" / "base"
            for name in ["final.zip", "best.zip", "last.zip"]:
                p = model_dir / name
                if p.exists():
                    current_model_path = p
                    break
        
        if not current_model_path or not current_model_path.exists():
            logger.warning(f"No model found for {ticker} (mode={mode}), skipping")
            continue

        # Predict
        model = PPO.load(current_model_path, device="cpu")
        preds = []
        for i in range(len(X)):
            action, _ = model.predict(X[i], deterministic=True)
            preds.append(int(action))
        y_pred = np.array(preds, dtype=np.int8)

        # Metrics
        metrics = _classification_metrics(y_true, y_pred)
        per_ticker[ticker] = metrics
        y_all_true.append(y_true)
        y_all_pred.append(y_pred)

    if not y_all_true:
        logger.error("No predictions generated.")
        return

    overall = _classification_metrics(np.concatenate(y_all_true), np.concatenate(y_all_pred))
    
    # 4. Save & Print
    output = {"overall": overall, "per_ticker": per_ticker}
    out_path = run_dir / "metrics.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    
    logger.info(f"Metrics updated at {out_path}")
    print(json.dumps(overall, indent=2))

    # Assertions
    tp, fp, tn, fn = overall["tp"], overall["fp"], overall["tn"], overall["fn"]
    support = overall["support"]
    assert tp + fp + tn + fn == support, f"Confusion matrix sum {tp+fp+tn+fn} != support {support}"
    assert 0.0 <= overall["buy_rate"] <= 1.0, "buy_rate out of range"
    assert 0.0 <= overall["positive_rate"] <= 1.0, "positive_rate out of range"
    logger.info("Assertions passed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate run metrics")
    parser.add_argument("--run-dir", type=str, required=True, help="Path to run directory")
    parser.add_argument("--config", type=str, help="Path to config override")
    parser.add_argument("--model", type=str, help="Path to specific model zip")
    parser.add_argument("--mode", type=str, default="finetune", choices=["finetune", "base"], help="Evaluation mode")
    
    args = parser.parse_args()
    evaluate_run(Path(args.run_dir), args.config, args.model and Path(args.model), args.mode)
