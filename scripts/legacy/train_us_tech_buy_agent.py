#!/usr/bin/env python
from __future__ import annotations

import argparse

from src.config import load_yaml
from scripts.run_experiment import run_experiment


def main() -> None:
    parser = argparse.ArgumentParser(description="Legacy entrypoint, delegated to config-driven pipeline.")
    parser.add_argument("--config", default="configs/base.yaml", help="Config path")
    parser.add_argument("--dry-run", action="store_true", help="Do not train")
    parser.add_argument("--force", action="store_true", help="Force retrain")
    args = parser.parse_args()

    cfg = load_yaml(args.config)
    run_experiment(cfg, dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
