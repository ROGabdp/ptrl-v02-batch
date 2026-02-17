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

## 文件與標註語言
- 本專案所有新文件、README 更新、程式註解與操作標註，統一使用正體中文。

## 檔案編碼規範
- 本專案所有文字檔（含 `README.md`、`AGENTS.md`、`*.md`、`*.py`、`*.ts`、`*.tsx`）必須使用 UTF-8（無 BOM）。
- 禁止使用 Big5、CP950、UTF-16 或系統預設 ANSI 編碼儲存專案檔案。
- 腳本寫檔必須明確指定 `encoding="utf-8"`。

## 防亂碼寫檔流程（必須遵守）

为避免出現 連續問號字元（例如四個問號） 或文字損壞，任何 agent 或腳本在寫入中文內容時，必須依下列流程執行：

1. 統一使用 UTF-8（無 BOM）寫檔。
2. 不可使用 shell 直接內嵌中文多行字串寫檔（容易受終端碼頁影響而變成 `?`）。
3. 若需以腳本寫入中文，請使用下列安全方式之一：
   - Python `Path.write_text(..., encoding="utf-8")`；
   - 內文字串使用 Unicode escape（`\uXXXX`）；
   - 或從已為 UTF-8 的範本檔載入後再寫回。
4. 寫檔後必做驗證：
   - 掃描是否出現 連續問號字元（例如四個問號）、`U+FFFD`（replacement char）。
   - 重讀並確認關鍵段落的正體中文顯示正常。
5. 若驗證失敗，不得提交或結束任務，必須先修正至通過驗證。

### 禁止事項
- 禁止使用 Big5、CP950、UTF-16、ANSI 寫入專案文字檔。
- 禁止在未驗證的情況下宣稱「編碼正常」。
