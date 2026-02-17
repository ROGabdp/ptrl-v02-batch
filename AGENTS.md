# Repository Guidelines

## Project Structure & Module Organization
- `src/`: core Python pipeline code (data loading, features, labels, training, evaluation, backtesting helpers).
- `scripts/`: CLI entrypoints for workflows such as `run_experiment`, `sweep`, `run_backtest`, `index_runs`, and metrics utilities.
- `api/`: FastAPI backend (`api.app`) with routes for data retrieval, job execution (train/backtest), and configuration management.
- `ui/src/`: React + TypeScript frontend (pages, components, API client).
- `configs/`: YAML configs (`base.yaml`, `daily_watchlist.yaml`, sweep grids, backtest config).
- Generated outputs: `runs/`, `reports/`, `backtests/` (treat as artifacts, not source).

## Build, Test, and Development Commands
- **Recommended (Windows)**:
  - Start: `scripts\dev_start.bat` (Starts Backend + Frontend + Browser)
  - Stop: `scripts\dev_stop.bat`



## Daily Decision Center (Phase 2 Milestone 3)

新增每日決策流程，用於產生次日交易訊號。

### 架構設計

1.  **Configuration**:
    -   `configs/daily_watchlist.yaml`: 獨立管理監控清單 (Tickers) 與策略參數 (Strategies)。
    -   支援 `per_ticker` 覆寫策略，確保不同標的可使用不同停損/停利設定。

2.  **Date Resolution (Auto-Date)**:
    -   API 接收 `date_override` 參數。
    -   若 User 未指定 End Date，系統自動預設為 **Today** (Local Time)。
    -   流程：`Override` > `Config` > `Today`.

3.  **Runtime Config Generation**:
    -   為確保 Backtest Job 執行參數的一致性與可追溯性，每次執行 Batch 時：
        1.  讀取 `daily_watchlist.yaml`。
        2.  為每個 Ticker 生成獨立的完整 YAML Config。
        3.  寫入 `reports/daily/runtime/<batch_id>/<ticker>.yaml` (Git Ignored)。
    -   Job 直接引用生成的 Runtime Config，避免 `conf_thresholds` 等複雜結構在 CLI 傳遞時發生解析錯誤。

4.  **UI Workflows**:
    -   **Run All**: 透過 `POST /api/daily/run-backtests` 觸發批次作業。
    -   **Results**: 前端輪詢 Job Status，完成後從 Job Artifacts 讀取 `bt_run_id`，並顯示 `end_date_summary`。

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
