# Repository Guidelines

## Project Structure & Module Organization
- `src/`: core Python pipeline code (data loading, features, labels, training, evaluation, backtesting helpers).
- `scripts/`: CLI entrypoints for workflows such as `run_experiment`, `sweep`, `run_backtest`, `index_runs`, and metrics utilities.
- `api/`: FastAPI backend (`api.app`) with read-only routes and service-layer readers for runs, registry, and backtests.
- `ui/src/`: React + TypeScript frontend (pages, components, API client).
- `configs/`: YAML configs (`base.yaml`, sweep grids, backtest config).
- Generated outputs: `runs/`, `reports/`, `backtests/` (treat as artifacts, not source).

## Build, Test, and Development Commands
- Install Python deps:
  - `python -m venv .venv && .\.venv\Scripts\Activate.ps1 && pip install -r requirements.txt`
- Validate training config without full run:
  - `python -m scripts.run_experiment --config configs/base.yaml --dry-run`
- Run sweep preview:
  - `python -m scripts.sweep --config configs/base.yaml --sweep configs/sweeps/label_grid.yaml --dry-run`
- Run a backtest:
  - `python -m scripts.run_backtest --config configs/backtest/base.yaml --ticker NVDA`
- Start API:
  - `uvicorn api.app:app --reload --port 8000`
- Start UI:
  - `cd ui; npm install; npm run dev`
- UI quality gates:
  - `cd ui; npm run build`
  - `cd ui; npm run lint`

## Coding Style & Naming Conventions
- Python: follow PEP 8, 4-space indentation, `snake_case` for modules/functions, `PascalCase` for classes.
- TypeScript/React: `PascalCase` components (`RunDetail.tsx`), `camelCase` variables/functions, colocate page logic under `ui/src/pages/`.
- Keep config overrides explicit with dotted keys (example: `--set label.horizon_days=40`).

## Testing Guidelines
- No dedicated automated test suite is currently committed; use reproducible CLI checks before opening a PR.
- Minimum validation for feature changes:
  - relevant `--dry-run` command for training/sweep/backtest paths;
  - `cd ui; npm run build && npm run lint` for frontend changes.
- When adding tests, use `tests/test_*.py` (Python) and `*.test.tsx` (UI) naming.

## Commit & Pull Request Guidelines
- Follow existing commit style from history: `feat(scope): ...`, `fix(scope): ...`, `chore: ...`.
- Keep commits focused (single concern) and reference touched areas (`api`, `ui`, `backtest`, `scripts`).
- PRs should include:
  - concise purpose and behavior impact;
  - commands run to validate changes;
  - linked issue/context;
  - screenshots for visible UI updates.

## Security & Configuration Tips
- Do not commit secrets, API keys, or local environment files.
- Prefer config-driven changes in `configs/` over hardcoded values.
- Review artifact directories (`runs/`, `backtests/`, `reports/`) before committing to avoid large or transient outputs.
