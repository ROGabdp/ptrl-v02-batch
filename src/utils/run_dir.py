from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


def now_local_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def make_run_id(config_hash: str, timestamp: str | None = None) -> str:
    ts = timestamp or now_local_timestamp()
    return f"{ts}__{config_hash[:8]}"


def ensure_run_tree(runs_root: str | Path, run_id: str) -> dict[str, Path]:
    run_dir = Path(runs_root) / run_id
    paths = {
        "run_dir": run_dir,
        "models_dir": run_dir / "models",
        "base_dir": run_dir / "models" / "base",
        "finetuned_dir": run_dir / "models" / "finetuned",
        "tb_dir": run_dir / "tb",
        "cache_dir": run_dir / "cache",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths


def git_commit_or_none(cwd: str | Path = ".") -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(cwd),
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out or None
    except Exception:
        return None


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
