from __future__ import annotations

import json
import os
import re
import sys
import threading
from datetime import datetime
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen
from typing import Any, Dict, List, Optional
from uuid import uuid4

from api.schemas.jobs import JobDetailResponse, JobType
from api.services.paths import BASE_DIR

JOBS_DIR = BASE_DIR / "reports" / "jobs"
RUNTIME_DIR = JOBS_DIR / "runtime"
_LOCK = threading.Lock()

_RUN_ID_RE = re.compile(r"(?<!bt_)run_id\s*[:=]\s*([A-Za-z0-9_]+)")
_RUN_DIR_RE = re.compile(r"run_dir\s*[:=]\s*(.+)")
_BT_RUN_ID_RE = re.compile(r"bt_run_id\s*[:=]\s*([A-Za-z0-9_]+)")
_BT_DIR_RE = re.compile(r"(?:output|out_dir)\s*[:=]\s*(.+)")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _ensure_jobs_dir() -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _to_relative(path: Path) -> str:
    return str(path.resolve().relative_to(BASE_DIR)).replace("\\", "/")


def _normalize_job_type(job_type: str) -> str:
    return "eval-metrics" if job_type == "eval_metrics" else job_type


def _is_within_repo(path: Path) -> bool:
    try:
        return os.path.commonpath([str(path.resolve()), str(BASE_DIR.resolve())]) == str(BASE_DIR.resolve())
    except ValueError:
        return False


def _resolve_repo_path(path_str: str, *, must_exist: bool = True) -> Path:
    raw = Path(path_str)
    candidate = raw if raw.is_absolute() else (BASE_DIR / raw)
    resolved = candidate.resolve()
    if not _is_within_repo(resolved):
        raise ValueError(f"Path must stay inside repository: {path_str}")
    if must_exist and not resolved.exists():
        raise ValueError(f"Path not found: {path_str}")
    return resolved


def _validate_overrides(overrides: List[str]) -> None:
    for item in overrides:
        if "=" not in item:
            raise ValueError(f"Invalid override '{item}', expected key=value")


def _new_job_id() -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = uuid4().hex[:8]
    return f"job_{ts}__{suffix}"


def _meta_path(job_id: str) -> Path:
    return RUNTIME_DIR / f"{job_id}.json"


def _log_path(job_id: str) -> Path:
    return RUNTIME_DIR / f"{job_id}.log"


def _write_meta(meta: Dict[str, Any]) -> None:
    path = _meta_path(meta["job_id"])
    path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_meta(job_id: str) -> Dict[str, Any]:
    path = _meta_path(job_id)
    if not path.exists():
        raise FileNotFoundError(job_id)
    return json.loads(path.read_text(encoding="utf-8"))


def _update_meta(job_id: str, **updates: Any) -> Dict[str, Any]:
    with _LOCK:
        meta = _read_meta(job_id)
        meta.update(updates)
        _write_meta(meta)
        return meta


def _parse_path_from_line(raw_path: str) -> str:
    cleaned = raw_path.strip().strip("'\"")
    candidate = Path(cleaned)
    if candidate.is_absolute():
        try:
            return _to_relative(candidate)
        except Exception:
            return cleaned.replace("\\", "/")
    return cleaned.replace("\\", "/")


def _extract_artifacts(line: str, artifacts: Dict[str, str]) -> None:
    m_run_id = _RUN_ID_RE.search(line)
    if m_run_id:
        run_id = m_run_id.group(1)
        artifacts["run_id"] = run_id
        artifacts.setdefault("run_dir", f"runs/{run_id}")

    m_run_dir = _RUN_DIR_RE.search(line)
    if m_run_dir:
        artifacts["run_dir"] = _parse_path_from_line(m_run_dir.group(1))

    m_bt_id = _BT_RUN_ID_RE.search(line)
    if m_bt_id:
        bt_run_id = m_bt_id.group(1)
        artifacts["bt_run_id"] = bt_run_id
        artifacts.setdefault("bt_dir", f"backtests/{bt_run_id}")

    m_bt_dir = _BT_DIR_RE.search(line)
    if m_bt_dir:
        artifacts["bt_dir"] = _parse_path_from_line(m_bt_dir.group(1))


def _tail_error_message(path: Path, max_lines: int = 80) -> Optional[str]:
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return None
    candidates = [ln.strip() for ln in lines[-max_lines:] if ln.strip()]
    if not candidates:
        return None
    for ln in reversed(candidates):
        if ln.startswith("[ERROR]"):
            return ln
    return candidates[-1]


def _duration_sec(started_at: Optional[str], ended_at: Optional[str]) -> Optional[float]:
    if not started_at or not ended_at:
        return None
    try:
        return max(0.0, (datetime.fromisoformat(ended_at) - datetime.fromisoformat(started_at)).total_seconds())
    except Exception:
        return None


def _args_preview(command: List[str], limit: int = 180) -> str:
    text = " ".join(command)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _to_job_detail(meta: Dict[str, Any]) -> JobDetailResponse:
    started_at = meta.get("started_at")
    ended_at = meta.get("ended_at")
    job_type = _normalize_job_type(str(meta.get("job_type", "train")))
    return JobDetailResponse(
        job_id=meta["job_id"],
        job_type=job_type,  # type: ignore[arg-type]
        status=meta.get("status", "QUEUED"),
        created_at=meta.get("created_at", _now_iso()),
        started_at=started_at,
        ended_at=ended_at,
        duration_sec=_duration_sec(started_at, ended_at),
        exit_code=meta.get("exit_code"),
        error_message=meta.get("error_message"),
        command=meta.get("command", []),
        args_preview=meta.get("args_preview") or _args_preview(meta.get("command", [])),
        cwd=meta.get("cwd", str(BASE_DIR)),
        artifacts=meta.get("artifacts") or meta.get("artifacts_hint") or {},
        runtime={
            "meta_path": meta.get("meta_path", ""),
            "log_path": meta.get("log_path", ""),
        },
    )


def _run_job(job_id: str) -> None:
    meta = _update_meta(job_id, status="RUNNING", started_at=_now_iso())
    cmd = meta["command"]
    cwd = meta["cwd"]
    log_file = _log_path(job_id)

    try:
        with log_file.open("a", encoding="utf-8", newline="") as out:
            out.write(f"$ {' '.join(cmd)}\n")
            out.flush()

            proc = Popen(
                cmd,
                cwd=cwd,
                stdout=PIPE,
                stderr=STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )

            artifacts = dict(meta.get("artifacts") or {})

            if proc.stdout is not None:
                for line in proc.stdout:
                    out.write(line)
                    out.flush()
                    _extract_artifacts(line, artifacts)

            code = proc.wait()
            status = "SUCCESS" if code == 0 else "FAILED"
            error_message = None if status == "SUCCESS" else _tail_error_message(log_file)
            if status == "FAILED" and not artifacts.get("artifacts_parse_error"):
                if meta.get("job_type") == "train" and ("run_id" not in artifacts or "run_dir" not in artifacts):
                    artifacts["artifacts_parse_error"] = "failed to parse run_id/run_dir from stdout"
                elif meta.get("job_type") == "backtest" and "bt_run_id" not in artifacts:
                    artifacts["artifacts_parse_error"] = "failed to parse bt_run_id from stdout"

            _update_meta(
                job_id,
                status=status,
                ended_at=_now_iso(),
                exit_code=code,
                error_message=error_message,
                artifacts=artifacts or {},
            )
    except Exception as exc:
        with log_file.open("a", encoding="utf-8") as out:
            out.write(f"\n[ERROR] {type(exc).__name__}: {exc}\n")
        _update_meta(
            job_id,
            status="FAILED",
            ended_at=_now_iso(),
            exit_code=-1,
            error_message=f"{type(exc).__name__}: {exc}",
        )


def _create_job(job_type: JobType, command: List[str], artifacts: Optional[Dict[str, str]] = None) -> JobDetailResponse:
    _ensure_jobs_dir()
    job_id = _new_job_id()
    log_path = _log_path(job_id)
    meta_path = _meta_path(job_id)
    log_path.touch(exist_ok=True)

    meta = {
        "job_id": job_id,
        "job_type": _normalize_job_type(job_type),
        "status": "QUEUED",
        "created_at": _now_iso(),
        "started_at": None,
        "ended_at": None,
        "exit_code": None,
        "error_message": None,
        "command": command,
        "args_preview": _args_preview(command),
        "cwd": str(BASE_DIR),
        "artifacts": artifacts or {},
        "log_path": _to_relative(log_path),
        "meta_path": _to_relative(meta_path),
    }
    _write_meta(meta)

    thread = threading.Thread(target=_run_job, args=(job_id,), daemon=True)
    thread.start()

    return _to_job_detail(meta)


def build_train_command(config_path: str, overrides: List[str], dry_run: bool) -> List[str]:
    config = _resolve_repo_path(config_path, must_exist=True)
    _validate_overrides(overrides)

    command = [
        sys.executable,
        "-m",
        "scripts.run_experiment",
        "--config",
        _to_relative(config),
    ]
    for item in overrides:
        command.extend(["--set", item])
    if dry_run:
        command.append("--dry-run")
    return command


def build_backtest_command(
    config_path: str,
    tickers: Optional[List[str]],
    model_path: Optional[str],
    start: Optional[str],
    end: Optional[str],
    overrides: List[str],
    dry_run: bool,
) -> List[str]:
    config = _resolve_repo_path(config_path, must_exist=True)
    _validate_overrides(overrides)

    if start and not _DATE_RE.match(start):
        raise ValueError("start must be YYYY-MM-DD")
    if end and not _DATE_RE.match(end):
        raise ValueError("end must be YYYY-MM-DD")

    command = [
        sys.executable,
        "-m",
        "scripts.run_backtest",
        "--config",
        _to_relative(config),
    ]

    if tickers:
        clean = [t.strip().upper() for t in tickers if t.strip()]
        if len(clean) == 1:
            command.extend(["--ticker", clean[0]])
        elif len(clean) > 1:
            command.extend(["--tickers", ",".join(clean)])

    if start:
        command.extend(["--start", start])
    if end:
        command.extend(["--end", end])

    if model_path:
        if not tickers or len([t for t in tickers if t.strip()]) != 1:
            raise ValueError("model_path requires exactly one ticker")
        model = _resolve_repo_path(model_path, must_exist=True)
        command.extend(["--model-path", _to_relative(model)])

    for item in overrides:
        command.extend(["--set", item])
    if dry_run:
        command.append("--dry-run")

    return command


def build_eval_metrics_command(run_id: str, mode: str, dry_run: bool) -> List[str]:
    if mode not in {"base", "finetune"}:
        raise ValueError("mode must be base or finetune")

    run_dir_rel = f"runs/{run_id}"
    _resolve_repo_path(run_dir_rel, must_exist=True)

    command = [
        sys.executable,
        "-m",
        "scripts.eval_metrics",
        "--run-dir",
        run_dir_rel,
        "--mode",
        mode,
    ]
    if dry_run:
        command.append("--dry-run")
    return command


def create_train_job(config_path: str, overrides: List[str], dry_run: bool) -> JobDetailResponse:
    command = build_train_command(config_path, overrides, dry_run)
    return _create_job("train", command)


def create_backtest_job(
    config_path: str,
    tickers: Optional[List[str]],
    model_path: Optional[str],
    start: Optional[str],
    end: Optional[str],
    overrides: List[str],
    dry_run: bool,
) -> JobDetailResponse:
    command = build_backtest_command(config_path, tickers, model_path, start, end, overrides, dry_run)
    return _create_job("backtest", command)


def create_eval_metrics_job(run_id: str, mode: str, dry_run: bool) -> JobDetailResponse:
    command = build_eval_metrics_command(run_id, mode, dry_run)
    return _create_job(
        "eval-metrics",
        command,
        artifacts={"run_id": run_id, "run_dir": f"runs/{run_id}"},
    )


def get_job(job_id: str) -> JobDetailResponse:
    return _to_job_detail(_read_meta(job_id))


def get_recent_jobs(
    *,
    limit: int = 100,
    status: Optional[str] = None,
    job_type: Optional[str] = None,
) -> List[JobDetailResponse]:
    _ensure_jobs_dir()
    items: List[Dict[str, Any]] = []
    for path in RUNTIME_DIR.glob("job_*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            items.append(data)
        except Exception:
            continue

    if status:
        status_norm = status.upper()
        items = [x for x in items if str(x.get("status", "")).upper() == status_norm]

    if job_type:
        type_norm = _normalize_job_type(job_type)
        items = [x for x in items if _normalize_job_type(str(x.get("job_type", ""))) == type_norm]

    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return [_to_job_detail(item) for item in items[:limit]]


def get_job_log(job_id: str, *, offset: int = 0, tail: int = 20000) -> Dict[str, Any]:
    if offset < 0:
        raise ValueError("offset must be >= 0")
    if tail <= 0:
        raise ValueError("tail must be > 0")

    path = _log_path(job_id)
    if not path.exists():
        raise FileNotFoundError(job_id)

    total_size = path.stat().st_size
    start = min(offset, total_size)
    is_truncated = False

    if offset == 0:
        start = max(0, total_size - tail)
        is_truncated = start > 0

    with path.open("rb") as fh:
        fh.seek(start)
        raw = fh.read()

    content = raw.decode("utf-8", errors="replace")
    next_offset = start + len(raw)

    return {
        "job_id": job_id,
        "content": content,
        "next_offset": next_offset,
        "is_truncated": is_truncated,
        "log_path": _to_relative(path),
    }