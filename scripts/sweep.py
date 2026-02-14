from __future__ import annotations

import argparse
import itertools
import random
from typing import Any

from src.config import apply_overrides, load_yaml
from scripts.run_experiment import run_experiment


def _grid(params: dict[str, list[Any]]) -> list[dict[str, Any]]:
    keys = list(params.keys())
    values = [params[k] for k in keys]
    out = []
    for combo in itertools.product(*values):
        out.append({k: v for k, v in zip(keys, combo)})
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Grid sweep runner")
    parser.add_argument("--config", default="configs/base.yaml", help="Base config yaml")
    parser.add_argument("--sweep", required=True, help="Sweep yaml")
    parser.add_argument("--dry-run", action="store_true", help="Dry-run every variant")
    parser.add_argument("--force", action="store_true", help="Force retrain")
    args = parser.parse_args()

    base_cfg = load_yaml(args.config)
    sweep_cfg = load_yaml(args.sweep)
    method = sweep_cfg.get("sweep", {}).get("method", "grid")
    if method != "grid":
        raise ValueError(f"Unsupported sweep.method={method}, only grid is supported")

    params = sweep_cfg.get("params", {})
    overrides = sweep_cfg.get("overrides", {})
    variants = _grid(params)

    if sweep_cfg.get("sweep", {}).get("shuffle", False):
        random.shuffle(variants)
    max_runs = sweep_cfg.get("sweep", {}).get("max_runs")
    if max_runs is not None:
        variants = variants[: int(max_runs)]

    print(f"sweep_variants: {len(variants)}")
    for idx, variant in enumerate(variants, start=1):
        cfg_variant = apply_overrides(base_cfg, {**overrides, **variant})
        print(f"[{idx}/{len(variants)}] overrides={variant}")
        run_experiment(cfg_variant, dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
