import json
import os
import re
import sys
import threading
from datetime import datetime
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen
from typing import Dict, List, Optional
from uuid import uuid4

from api.schemas.jobs import Job, JobType
from api.services.paths import BASE_DIR

JOBS_DIR = BASE_DIR / "reports" / "jobs"
RUNTIME_DIR = JOBS_DIR / "runtime"
_LOCK = threading.Lock()

_RUN_ID_RE = re.compile(r"(?<!bt_)run_id\s*[:=]\s*([A-Za-z0-9_]+)")
_BT_RUN_ID_RE = re.compile(r"bt_run_id\s*[:=]\s*([A-Za-z0-9_]+)")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _ensure_jobs_dir() -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _to_relative(path: Path) -> str:
    return str(path.resolve().relative_to(BASE_DIR)).replace("\\", "/")


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


def _write_meta(meta: Dict) -> None:
    path = _meta_path(meta["job_id"])
    path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_meta(job_id: str) -> Dict:
    path = _meta_path(job_id)
    if not path.exists():
        raise FileNotFoundError(job_id)
    return json.loads(path.read_text(encoding="utf-8"))


def _update_meta(job_id: str, **updates: Dict) -> Dict:
    with _LOCK:
        meta = _read_meta(job_id)
        meta.update(updates)
        _write_meta(meta)
        return meta


def _extract_artifact_hint(line: str, artifacts_hint: Dict[str, str]) -> None:
    m_run = _RUN_ID_RE.search(line)
    if m_run:
        artifacts_hint["run_id"] = m_run.group(1)
    m_bt = _BT_RUN_ID_RE.search(line)
    if m_bt:
        artifacts_hint["bt_run_id"] = m_bt.group(1)


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

            artifacts_hint = dict(meta.get("artifacts_hint") or {})

            if proc.stdout is not None:
                for line in proc.stdout:
                    out.write(line)
                    out.flush()
                    _extract_artifact_hint(line, artifacts_hint)

            code = proc.wait()
            status = "SUCCESS" if code == 0 else "FAILED"
            _update_meta(
                job_id,
                status=status,
                ended_at=_now_iso(),
                artifacts_hint=artifacts_hint or None,
            )
    except Exception as exc:
        with log_file.open("a", encoding="utf-8") as out:
            out.write(f"\n[ERROR] {type(exc).__name__}: {exc}\n")
        _update_meta(job_id, status="FAILED", ended_at=_now_iso())


def _create_job(job_type: JobType, command: List[str], artifacts_hint: Optional[Dict[str, str]] = None) -> Job:
    _ensure_jobs_dir()
    job_id = _new_job_id()
    log_path = _log_path(job_id)
    meta_path = _meta_path(job_id)
    log_path.touch(exist_ok=True)

    meta = {
        "job_id": job_id,
        "job_type": job_type,
        "status": "QUEUED",
        "created_at": _now_iso(),
        "started_at": None,
        "ended_at": None,
        "command": command,
        "cwd": str(BASE_DIR),
        "artifacts_hint": artifacts_hint or None,
        "log_path": _to_relative(log_path),
        "meta_path": _to_relative(meta_path),
    }
    _write_meta(meta)

    thread = threading.Thread(target=_run_job, args=(job_id,), daemon=True)
    thread.start()

    return Job(**meta)


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


def create_train_job(config_path: str, overrides: List[str], dry_run: bool) -> Job:
    command = build_train_command(config_path, overrides, dry_run)
    return _create_job("train", command)


def create_backtest_job(
    config_path: str,
    tickers: Optional[List[str]],
    start: Optional[str],
    end: Optional[str],
    overrides: List[str],
    dry_run: bool,
) -> Job:
    command = build_backtest_command(config_path, tickers, start, end, overrides, dry_run)
    return _create_job("backtest", command)


def create_eval_metrics_job(run_id: str, mode: str, dry_run: bool) -> Job:
    command = build_eval_metrics_command(run_id, mode, dry_run)
    return _create_job("eval_metrics", command, artifacts_hint={"run_id": run_id})


def get_job(job_id: str) -> Job:
    return Job(**_read_meta(job_id))


def get_recent_jobs(limit: int = 50) -> List[Job]:
    _ensure_jobs_dir()
    items = []
    for path in RUNTIME_DIR.glob("job_*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            items.append(data)
        except Exception:
            continue

    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return [Job(**item) for item in items[:limit]]


def get_job_log(job_id: str) -> str:
    path = _log_path(job_id)
    if not path.exists():
        raise FileNotFoundError(job_id)
    return path.read_text(encoding="utf-8", errors="replace")
