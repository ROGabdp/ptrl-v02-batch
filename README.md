# ptrl-v02-batch

本專案採用「設定檔驅動」訓練流程，具備可追溯與可重現的 run 目錄：

- `run_id` 格式固定為：`YYYYMMDD_HHMMSS__<config_hash8>`
- 所有輸出一律寫入：`runs/<run_id>/...`
- 支援 `--dry-run`、resume/skip、`--force`、grid sweep

## 環境需求

- Python `3.10+`
- 建議使用 Windows PowerShell + venv

## 快速開始（Windows PowerShell）

在專案根目錄執行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## GUI Dashboard (Phase 1)

本專案提供一個本地 Web UI，用於瀏覽 Registry、Training Runs 與 Backtests 結果。

### 1. 啟動後端 API (Port 8000)

使用 FastAPI 提供唯讀資料介面：

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn api.app:app --reload --port 8000
```

- API 文件：http://localhost:8000/docs
- 測試：http://localhost:8000/api/registry/best

### 2. 啟動前端 UI (Port 5173)

使用 React + Vite (已設定 Proxy 轉發 API 請求)：

```powershell
cd ui
npm install  # 首次執行
npm run dev
```

- 瀏覽器開啟：http://localhost:5173
- 功能：
  - **Dashboard**: 查看最佳模型與最近執行紀錄。Phase 1.5 新增 Precision, Lift, Label, Pos Rate 等關鍵指標。
  - **Registry**: 篩選與瀏覽所有已索引模型。Phase 1.5 新增 Lift/Precision 過濾器與詳細指標 (TP/FP, Pos Rate)。
  - **Runs**: 查看訓練參數與產出模型。Phase 1.5 支援查看所有 Checkpoints 與複製模型路徑。
  - **Backtests**: 查看回測績效、權益曲線 (Equity Curve)。Phase 1.5 新增策略參數摘要 (Strategy Summary)、最大回撤區間 (MDD Window) 與近期交易列表 (Recent Trades)。

## 訓練前檢查（建議先跑）

先做乾跑，確認 config 與流程可正常建立 run：

```powershell
.\.venv\Scripts\Activate.ps1
python -m scripts.run_experiment --config configs/base.yaml --dry-run
```

若成功，stdout 會顯示：

- `run_id: ...`
- `run_dir: runs/<run_id>`
- `manifest: runs/<run_id>/manifest.json`

## 正式訓練（單次）

```powershell
.\.venv\Scripts\Activate.ps1
python -m scripts.run_experiment --config configs/base.yaml
```

預設行為：

- pretrain universe：`NVDA, MSFT, AAPL, AMZN, META, AVGO, GOOGL, TSLA, NFLX, PLTR, TSM`
- finetune tickers：`NVDA, GOOGL, TSM`
- label：`horizon_days=20`、`threshold=0.10`

## 訓練監控（TensorBoard）

訓練過程會把 TensorBoard logs 寫在 `runs/<run_id>/tb/`。

啟動方式：

```powershell
.\.venv\Scripts\Activate.ps1
tensorboard --logdir runs --port 6006
```

瀏覽器開啟：

- `http://localhost:6006`

## Sweep（批次參數掃描）

```powershell
.\.venv\Scripts\Activate.ps1
python -m scripts.sweep --config configs/base.yaml --sweep configs/sweeps/label_grid.yaml
```

只檢查 sweep 展開流程可先用：

```powershell
python -m scripts.sweep --config configs/base.yaml --sweep configs/sweeps/label_grid.yaml --dry-run
```

## 常用參數

- 強制重訓（忽略 `final.zip` 的 skip 判斷）：

```powershell
python -m scripts.run_experiment --config configs/base.yaml --force
```

- 臨時覆寫設定（dotted path）：

```powershell
python -m scripts.run_experiment --config configs/base.yaml --set label.horizon_days=40 --set label.threshold=0.15
python -m scripts.run_experiment --config configs/base.yaml --set train.finetune.tickers='["NVDA","TSM"]'
```

## Resume / Skip 規則

- 若 `runs/<run_id>/models/base/final.zip` 已存在且未加 `--force`，會跳過 base 訓練。
- 若 `runs/<run_id>/models/finetuned/<TICKER>/final.zip` 已存在且未加 `--force`，會跳過該 ticker 微調。
- 若只有 `checkpoint_step_<N>.zip` / `best.zip` / `last.zip`，但沒有 `final.zip`，會嘗試從最近狀態續跑。

## 重跑評估 (Re-run Metrics)

若需對已存在的 run 重算評估指標（含 `buy_rate`, `positive_rate`, confusion matrix 等），可使用 `scripts.eval_metrics`：

```powershell
# 基本用法 (預設使用 finetuned 模型)
python -m scripts.eval_metrics --run-dir runs/<run_id>

# 指定使用 Base Model 評估所有 Tickers
python -m scripts.eval_metrics --run-dir runs/<run_id> --mode base

# 強制指定特定 Model 檔
python -m scripts.eval_metrics --run-dir runs/<run_id> --model runs/<run_id>/models/base/best.zip
```

這將會更新 `runs/<run_id>/metrics.json`。

## 執行產出

每次執行都會建立獨立目錄：

- `runs/<run_id>/config.yaml`
- `runs/<run_id>/data_manifest.json`
- `runs/<run_id>/metrics.json`
- `runs/<run_id>/manifest.json`
- `runs/<run_id>/tb/`
- `runs/<run_id>/cache/`
- `runs/<run_id>/models/base/{checkpoint_step_<N>.zip,best.zip,last.zip,final.zip}`
- `runs/<run_id>/models/finetuned/<TICKER>/{checkpoint_step_<N>.zip,best.zip,last.zip,final.zip}`

## Label Balance Finder

針對單一 ticker，搜尋 `(horizon_days, target_return)` 組合，使事件比例 `positive_rate` 接近指定目標（預設 50%），並同時輸出 train/val 的事件比例，幫助挑出 train/val 分佈更接近的 label 設定。

### 基本用法

```powershell
.\.venv\Scripts\Activate.ps1
python -m scripts.find_label_balance --ticker GOOGL --config configs/base.yaml --horizons 10,20,40 --returns 0.05,0.08,0.10,0.12,0.15 --target-rate 0.5 --top-k 10
```

### Dry Run（預覽模式）

```powershell
python -m scripts.find_label_balance --ticker NVDA --dry-run
```

### 輸出到檔案

最簡方式：加上 `--save`，腳本會自動產生可讀檔名並寫入 `reports/label_balance/`：

```powershell
# 自動命名 CSV（預設格式）
python -m scripts.find_label_balance --ticker TSM --config configs/base.yaml --horizons 10,20,60,120 --returns 0.1,0.15,0.2,0.25 --split both --target-rate 0.5 --top-k 10 --save

# 自動命名 JSON
python -m scripts.find_label_balance --ticker TSM --horizons 10,20,60,120 --returns 0.1,0.15,0.2,0.25 --save --format json
```

也可手動指定路徑（向後相容）：

```powershell
python -m scripts.find_label_balance --ticker NVDA --out label_balance__NVDA__both__20260215.csv
python -m scripts.find_label_balance --ticker NVDA --out result.json
```

- 輸出檔預設位置為 `reports/label_balance/`，**不會**寫到 `runs/`。
- 預設不寫檔，僅輸出到 stdout。
- `--save` + `--out` 同時給時，以 `--out` 為準。

### 排序規則

- `--split both`（預設）：依 `|val_rate - target|` → `|train_rate - target|` → `|train - val|` → `N` 排序
- `--split val`：僅依 `|val_rate - target|` → `N_val` 排序
- `--split train`：僅依 `|train_rate - target|` → `N_train` 排序

## Model Registry

當 `runs/` 裡的 run 越來越多，很難一眼看出每個 ticker 有哪些模型、各自的 label 目標和 metrics。`index_runs` 工具會掃描所有 run，建立兩份索引：

- **`registry_models`**：所有 ticker-model 的完整列表（每個 ticker × 每個 run 為一列），含完整 metrics、模型路徑、label 目標。
- **`registry_best_by_ticker`**：依選模邏輯，為每個 ticker 挑出最佳模型。

### 基本用法

```powershell
.\.venv\Scripts\Activate.ps1
python -m scripts.index_runs --runs-dir runs --out-dir reports/registry
```

每次執行都會**覆蓋更新** `reports/registry/` 下四個檔案：
`registry_models.csv` / `.json`、`registry_best_by_ticker.csv` / `.json`

### 選模流程（best_by_ticker）

1. **確保比亂買好**：`lift >= 1.10`（precision / positive_rate；至少比隨機買入提升 10%，避免「事件太容易，亂買也準」的假象）
2. **確保事件穩定**：`tp >= 30`（避免事件太稀有讓 lift/precision 虛高）
3. **（可選）限制出手頻率**：若指定 `--buy-rate-max`，才過濾 `buy_rate <= 上限`
4. **排序**（預設 `precision_first`）：precision ↓ → lift ↓ → buy_rate ↑ → support ↓

> **為什麼 buy_rate 不做硬過濾？**
> `buy_rate` 代表出手頻率，是交易偏好而非品質指標。一個 buy_rate=0.50 但 precision=0.70 的模型，仍然是好模型（只是比較積極）。
> 真正判斷「是否亂買」應看 `lift` 和 `precision`。如果你想要更保守的策略（少出手），可以加 `--buy-rate-max 0.35`。

### 若無模型通過

若某 ticker 無任何模型通過過濾，工具會放寬門檻（`lift >= 1.0`、`tp >= 1`），挑出最接近的候選，並標記 `best_status="NO_PASS: <原因>"`。

### 用法範例

```powershell
# 預設（buy_rate 不過濾，lift >= 1.10，tp >= 30）
python -m scripts.index_runs --runs-dir runs --out-dir reports/registry

# 放寬 lift 門檻（包含更接近亂買水準的模型）
python -m scripts.index_runs --runs-dir runs --out-dir reports/registry --lift-min 1.05

# 啟用少出手限制（更保守策略）
python -m scripts.index_runs --runs-dir runs --out-dir reports/registry --buy-rate-max 0.35

# 調整 min_tp（要求更多 TP 樣本）
python -m scripts.index_runs --runs-dir runs --out-dir reports/registry --min-tp 50

# 改用 lift 優先排序
python -m scripts.index_runs --sort-preset lift_first

# 只輸出 CSV / 包含缺檔 run
python -m scripts.index_runs --format csv --include-incomplete
```

## Backtesting（回測）

使用訓練出的模型進行 config-driven 回測，支援 per-ticker 策略覆寫與視覺化輸出。

### 輸出位置

- 回測產物寫入 `backtests/<bt_run_id>/`（**不進 git**，已加入 `.gitignore`）
- 每個 ticker 會產生獨立的 `bt_run_id` 目錄
- 每次回測輸出：`config.yaml`、`selection.json`、`trades.csv`、`equity.csv`、`metrics.json`、`summary.txt`、`plots/equity_curve.png`
- **跟單摘要**：另外產出 `end_date_summary_<TICKER>_<START>_<END>.txt`，包含市場數據、AI 信號、帳戶狀態、持倉停損/停利價位、明日交易建議

### 預設日期區間

CLI 未指定 `--start` / `--end` 時，使用 `configs/backtest/base.yaml` 中的預設值：

| 欄位 | 預設值 |
|------|--------|
| start | 2017-10-16 |
| end | 2023-10-15 |

若只指定 `--start`（未給 `--end`），`end` **自動使用今天日期**，並自動更新本地 CSV 快取。

### 模型來源

預設從 `reports/registry/registry_best_by_ticker.csv` 選模。也可透過 `--model-path` 強制指定。

回測會自動從 registry 對應的 `config_path` 讀取訓練 config，確保特徵（feature_cols、feature params）與訓練時一致。

### per_ticker 策略覆寫

`configs/backtest/base.yaml` 中的 `strategy` 為全域預設，`per_ticker` 區塊可為個別 ticker 覆寫差異值（深層 merge）。

例如 TSM 使用更寬的停損：

```yaml
per_ticker:
  TSM:
    exit:
      stop_loss_pct: 0.10   # 全域預設 0.08，TSM 改為 0.10
```

### 基本用法

```powershell
.\.venv\Scripts\Activate.ps1

# 1) 用預設區間（2017-10-16 ~ 2023-10-15）
python -m scripts.run_backtest --config configs/backtest/base.yaml --ticker NVDA

# 2) 只指定 start，end 自動 today（自動更新資料）
python -m scripts.run_backtest --config configs/backtest/base.yaml --ticker NVDA --start 2025-12-09

# 3) 指定完整區間
python -m scripts.run_backtest --config configs/backtest/base.yaml --ticker NVDA --start 2025-12-09 --end 2026-02-14

# 4) 多檔
python -m scripts.run_backtest --config configs/backtest/base.yaml --tickers NVDA,GOOGL,TSM

# 5) 覆寫策略參數
python -m scripts.run_backtest --config configs/backtest/base.yaml --ticker TSM --set strategy.exit.stop_loss_pct=0.10

# 6) dry-run（只印摘要，不回測）
python -m scripts.run_backtest --config configs/backtest/base.yaml --ticker GOOGL --dry-run

# 7) 關閉畫圖
python -m scripts.run_backtest --config configs/backtest/base.yaml --ticker GOOGL --no-plot
```

## 常見問題

- `ModuleNotFoundError: No module named 'yaml'`：
  - 先確認已啟用 venv，再執行 `pip install -r requirements.txt`。
- `tensorboard` 指令找不到：
  - 確認 venv 已啟用並重新執行 `pip install -r requirements.txt`。
- PowerShell 無法啟用腳本：
  - 可先執行 `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`（僅當前視窗有效）。

## GUI Phase 2 - Jobs (Milestone 1)

Phase 2 Milestone 1 adds basic task execution from UI/API for three actions:

- Train: `python -m scripts.run_experiment --config <path> [--set ...]`
- Backtest: `python -m scripts.run_backtest --config <path> [--ticker/--tickers] [--start] [--end] [--set ...]`
- Recompute metrics: `python -m scripts.eval_metrics --run-dir runs/<run_id> [--mode base|finetune]`

### API endpoints

- `POST /api/jobs/train`
- `POST /api/jobs/backtest`
- `POST /api/jobs/eval-metrics`
- `GET /api/jobs/recent?limit=50`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/log`

### Job artifacts

- Metadata: `reports/jobs/<job_id>.json` (recommended to keep)
- Logs: `reports/jobs/<job_id>.log`
- API returns `artifacts_hint` with parsed `run_id` / `bt_run_id` when available, so UI can jump to Run/Backtest detail.

### UI usage

1. Start backend and frontend:

```powershell
uvicorn api.app:app --reload --port 8000
cd ui
npm run dev
```

2. Use these pages:

- `/actions`: simple forms to trigger Train/Backtest jobs.
- `/runs/:runId`: click **Recompute Metrics** to create eval job.
- `/registry` and Dashboard best-model cards: click **Run Backtest**.
- `/jobs`: monitor recent jobs (status polling every few seconds).
- `/jobs/:jobId`: inspect command metadata and live log output.
