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

## 常見問題

- `ModuleNotFoundError: No module named 'yaml'`：
  - 先確認已啟用 venv，再執行 `pip install -r requirements.txt`。
- `tensorboard` 指令找不到：
  - 確認 venv 已啟用並重新執行 `pip install -r requirements.txt`。
- PowerShell 無法啟用腳本：
  - 可先執行 `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`（僅當前視窗有效）。
