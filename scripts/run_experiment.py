from __future__ import annotations

import argparse
from datetime import datetime
from typing import Any

from src.config import apply_overrides, config_hash, dump_yaml, load_yaml, parse_set_values
from src.utils.run_dir import ensure_run_tree, git_commit_or_none, make_run_id, write_json


def _manifest_skeleton(cfg: dict[str, Any], run_id: str, cfg_hash: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "git_commit": git_commit_or_none("."),
        "seed": cfg["run"]["seed"],
        "config_hash": cfg_hash,
        "base_final_path": None,
        "per_ticker_final_paths": {},
        "data_cutoff_dates": {},
        "feature_cache_keys": {},
    }


def run_experiment(cfg: dict[str, Any], dry_run: bool = False, force: bool = False) -> dict[str, Any]:
    cfg = dict(cfg)
    if not cfg["features"].get("feature_cols"):
        raise ValueError("features.feature_cols must be provided in config")

    cfg_hash = config_hash(cfg)
    run_id = make_run_id(cfg_hash)
    paths = ensure_run_tree(cfg["run"]["runs_root"], run_id)
    run_dir = paths["run_dir"]

    cfg_out = dict(cfg)
    cfg_out["run"] = dict(cfg_out["run"])
    cfg_out["run"]["run_id"] = run_id
    cfg_out["run"]["force"] = force
    cfg_out["run"]["dry_run"] = dry_run
    dump_yaml(run_dir / "config.yaml", cfg_out)

    manifest = _manifest_skeleton(cfg, run_id, cfg_hash)
    data_manifest: dict[str, Any] = {"tickers": {}, "benchmark": cfg["universe"]["benchmark"]}
    metrics: dict[str, Any] = {}

    print(f"run_id: {run_id}")
    print(f"run_dir: {run_dir.as_posix()}")

    if dry_run:
        tickers = cfg["universe"]["tickers"]
        for t in tickers:
            manifest["feature_cache_keys"][t] = "dry-run"
            manifest["data_cutoff_dates"][t] = None
            data_manifest["tickers"][t] = {"rows": None, "cutoff_date": None, "feature_cache_key": "dry-run"}
        base_final = (paths["base_dir"] / "final.zip").as_posix()
        manifest["base_final_path"] = base_final
        for t in cfg["train"]["finetune"]["tickers"]:
            manifest["per_ticker_final_paths"][t] = (paths["finetuned_dir"] / t / "final.zip").as_posix()
        metrics = {"overall": {}, "per_ticker": {}, "dry_run": True}
    else:
        from src.data.loader import fetch_all_stock_data
        from src.eval.metrics import evaluate_models_on_validation
        from src.features.builder import build_all_features
        from src.splits.time_split import split_train_val
        from src.train.trainer import train_base, train_finetune_one

        raw_data = fetch_all_stock_data(cfg)
        feature_data, cache_keys = build_all_features(
            cfg=cfg,
            raw_data=raw_data,
            use_cache=bool(cfg["features"]["cache"].get("enabled", True)),
        )
        train_data, val_data, cutoff_dates = split_train_val(cfg, raw_data, feature_data)

        for t, key in cache_keys.items():
            manifest["feature_cache_keys"][t] = key
            cutoff = cutoff_dates.get(t)
            manifest["data_cutoff_dates"][t] = cutoff
            data_manifest["tickers"][t] = {
                "rows": int(len(feature_data[t])),
                "cutoff_date": cutoff,
                "feature_cache_key": key,
            }

        pretrain_status, base_final = train_base(
            cfg=cfg,
            train_data=train_data,
            base_dir=paths["base_dir"],
            tb_dir=paths["tb_dir"],
            dry_run=False,
            force=force,
        )
        manifest["base_final_path"] = base_final
        print(f"base_stage: {pretrain_status} -> {base_final}")

        ft_tickers = [t for t in cfg["train"]["finetune"]["tickers"] if t in train_data]
        for ticker in ft_tickers:
            t_train = {ticker: train_data[ticker]}
            t_eval = {ticker: val_data.get(ticker, train_data[ticker])}
            stage_dir = paths["finetuned_dir"] / ticker
            ft_status, final_path = train_finetune_one(
                cfg=cfg,
                ticker=ticker,
                ticker_train_data=t_train,
                ticker_eval_data=t_eval,
                base_final_path=base_final,
                finetune_stage_dir=stage_dir,
                tb_dir=paths["tb_dir"],
                dry_run=False,
                force=force,
            )
            manifest["per_ticker_final_paths"][ticker] = final_path
            print(f"finetune_{ticker}: {ft_status} -> {final_path}")

        metrics = evaluate_models_on_validation(
            feature_cols=cfg["features"]["feature_cols"],
            val_data={k: v for k, v in val_data.items() if k in manifest["per_ticker_final_paths"]},
            ticker_model_paths=manifest["per_ticker_final_paths"],
            threshold=float(cfg["label"]["threshold"]),
        )

    write_json(run_dir / "data_manifest.json", data_manifest)
    write_json(run_dir / "metrics.json", metrics)
    manifest["end_time"] = datetime.now().isoformat()
    write_json(run_dir / "manifest.json", manifest)
    print(f"manifest: {(run_dir / 'manifest.json').as_posix()}")

    return {"run_id": run_id, "run_dir": str(run_dir), "manifest": manifest, "metrics": metrics}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run config-driven US tech buy-agent experiment.")
    parser.add_argument("--config", required=True, help="Path to config yaml")
    parser.add_argument("--dry-run", action="store_true", help="Plan only and generate run artifacts without training")
    parser.add_argument("--force", action="store_true", help="Force retrain even when final.zip already exists")
    parser.add_argument("--set", action="append", default=[], help="Override, format: key=value")
    args = parser.parse_args()

    cfg = load_yaml(args.config)
    if args.set:
        cfg = apply_overrides(cfg, parse_set_values(args.set))
    run_experiment(cfg, dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
