# Repository Guidelines

## Project Structure & Module Organization
- `src/` contains production code, split by responsibility: `data/`, `features/`, `splits/`, `train/`, `eval/`, `envs/`, and shared helpers in `config.py` and `utils/`.
- `scripts/` contains entry points: `run_experiment.py` (single run) and `sweep.py` (grid runs). `scripts/legacy/` holds older training/data artifacts; avoid adding new logic there.
- `configs/` stores YAML configs (`base.yaml`) and sweep definitions (`configs/sweeps/*.yaml`).
- `runs/<run_id>/` is generated output (models, manifests, TensorBoard logs). Treat it as runtime artifact, not source.

## Build, Test, and Development Commands
- Setup (PowerShell):
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```
- Dry-run validation:
  ```powershell
  python -m scripts.run_experiment --config configs/base.yaml --dry-run
  ```
  Confirms config parsing and run directory creation without training.
- Full run:
  ```powershell
  python -m scripts.run_experiment --config configs/base.yaml
  ```
- Sweep:
  ```powershell
  python -m scripts.sweep --config configs/base.yaml --sweep configs/sweeps/label_grid.yaml --dry-run
  ```

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation, type hints, and `snake_case` for functions/variables/modules.
- Keep modules focused by stage (`train_*`, `split_*`, `build_*`) and prefer explicit dictionary keys for config-driven behavior.
- Use UTF-8 text files; keep YAML keys stable and readable (no unnecessary reordering).

## Testing Guidelines
- No dedicated `tests/` suite is currently present. Use repeatable smoke checks:
  - `run_experiment --dry-run`
  - `sweep --dry-run`
- When adding logic, include small deterministic checks close to the changed module and verify `runs/<run_id>/manifest.json` and `metrics.json` are generated.

## Commit & Pull Request Guidelines
- Git history is not available in this workspace snapshot (`.git` missing), so use clear imperative commit subjects, e.g., `Add cache key validation in feature builder`.
- PRs should include:
  - Purpose and scope
  - Configs used to validate (`configs/base.yaml`, sweep file, overrides)
  - Before/after behavior (logs or key metric/manifests paths)
  - Any runtime or reproducibility impact

## Security & Configuration Tips
- Do not commit secrets or API keys in YAML/config overrides.
- Keep large artifacts (`runs/`, model `.zip` files, TensorBoard logs) out of commits unless explicitly required.
