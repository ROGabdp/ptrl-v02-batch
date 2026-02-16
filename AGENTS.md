# Repository Guidelines

## Project Structure & Module Organization
Core implementation lives in `src/` and is split by responsibility:
- `src/data/` data loading
- `src/features/` feature engineering
- `src/splits/` train/validation split logic
- `src/train/` model training stages
- `src/eval/` evaluation metrics
- `src/registry/` run indexing and model selection

CLI entry points live in `scripts/` (for example `scripts/run_experiment.py`, `scripts/sweep.py`, `scripts/eval_metrics.py`).  
Config files are in `configs/` (base config plus sweep configs).  
Run artifacts are written to `runs/<run_id>/`; aggregated reports go to `reports/`.

## Build, Test, and Development Commands
Use PowerShell from repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```powershell
python -m scripts.run_experiment --config configs/base.yaml --dry-run
```
Validates config and run directory generation without training.

```powershell
python -m scripts.run_experiment --config configs/base.yaml
python -m scripts.sweep --config configs/base.yaml --sweep configs/sweeps/label_grid.yaml
python -m scripts.eval_metrics --run-dir runs/<run_id>
python -m scripts.index_runs --runs-dir runs --out-dir reports/registry
```

## Coding Style & Naming Conventions
- Python 3.10+ with 4-space indentation and type hints (`dict[str, Any]`, etc.).
- Favor small, single-purpose functions and explicit argument names.
- Use `snake_case` for functions/variables/files, `UPPER_SNAKE_CASE` for constants.
- Keep modules domain-focused (data/features/train/eval) and avoid cross-layer shortcuts.
- YAML keys use dotted override paths (for example `--set label.threshold=0.15`).

## Testing Guidelines
There is no dedicated `tests/` suite yet. Minimum validation before PR:
- Run `--dry-run` for config/path integrity.
- Run one real experiment on `configs/base.yaml`.
- If you change metrics or registry logic, re-run `scripts.eval_metrics` and `scripts.index_runs` on a recent run and verify output files in `runs/` and `reports/registry/`.

## Commit & Pull Request Guidelines
- Prefer Conventional Commit style seen in history: `feat: ...`, `fix: ...`, `chore: ...`.
- Keep commits focused and scoped to one change.
- PRs should include:
  - what changed and why
  - config or CLI examples to reproduce
  - impacted paths (for example `src/eval/metrics.py`, `configs/base.yaml`)
  - before/after notes for metrics or registry outputs when behavior changes

## Security & Configuration Tips
- Do not commit secrets or API keys.
- Keep raw datasets and large model artifacts out of git; `.gitignore` should cover generated outputs under `runs/`.
