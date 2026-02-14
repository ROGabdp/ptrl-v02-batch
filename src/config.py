from __future__ import annotations

import copy
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a mapping: {path}")
    return data


def dump_yaml(path: str | Path, data: dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=False)


def deep_copy(data: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(data)


def _set_dotted(cfg: dict[str, Any], dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    cur = cfg
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value


def apply_overrides(cfg: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    out = deep_copy(cfg)
    for k, v in overrides.items():
        _set_dotted(out, k, v)
    return out


def parse_set_values(pairs: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for item in pairs:
        if "=" not in item:
            raise ValueError(f"Invalid override '{item}', expected key=value")
        k, raw_v = item.split("=", 1)
        out[k.strip()] = yaml.safe_load(raw_v.strip())
    return out


def _normalize_for_hash(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _normalize_for_hash(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_for_hash(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def canonical_experiment_config(cfg: dict[str, Any]) -> dict[str, Any]:
    run_cfg = cfg.get("run", {})
    canonical = {
        "run": {"seed": run_cfg.get("seed", 42)},
        "universe": cfg.get("universe", {}),
        "data": cfg.get("data", {}),
        "splits": cfg.get("splits", {}),
        "label": cfg.get("label", {}),
        "features": cfg.get("features", {}),
        "train": cfg.get("train", {}),
    }
    return _normalize_for_hash(canonical)


def canonical_yaml_text(cfg: dict[str, Any]) -> str:
    canonical = canonical_experiment_config(cfg)
    return json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def config_hash(cfg: dict[str, Any]) -> str:
    text = canonical_yaml_text(cfg)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
