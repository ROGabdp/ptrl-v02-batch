## **Phase 2 — Milestone 1 Prompt**

你是資深全端工程師，請在我本機 repo `D:\000-github-repositories\ptrl-v02-batch` 上完成 Phase 2 / Milestone 1 的改動。

### **0\) 重要規則（必須遵守）**

1. **先確認工作目錄**是 `ptrl-v02-batch` repo 根目錄。

2. **必須開新分支**再開始改：

   * 從目前包含 Phase 1.5 的分支（例如 `phase1`）切出

   * 新分支命名：`phase2-m1`

   * 指令範例（你自行判斷 base branch 名稱）：

     * `git checkout phase1`

     * `git pull`

     * `git checkout -b phase2-m1`

3. \*\*Phase 2 是 UI 可操作（可觸發任務）\*\*的階段，但 Milestone 1 要做到「最小可交付」：先把「觸發訓練/回測/重算評估」做成後端 job \+ 前端按鈕，並能看到 job 狀態與 log（不要求分散式、也不要求登入）。

4. 所有產出仍遵守既有規範：

   * 訓練輸出：`runs/<run_id>/...`

   * 回測輸出：`backtests/<bt_run_id>/...` 且 **backtests 在 .gitignore**（Phase 1 已做）

   * reports 會 commit 到 git（registry、label\_balance 等）

5. 不能破壞既有 Phase 1.5 的 read-only dashboard；新增功能要向後兼容。

---

### **1\) Repo 現況（你需要先理解）**

專案結構與職責（摘要）：

* `configs/`：訓練 YAML（含 `configs/base.yaml`、sweeps）

* `scripts/`：CLI 入口

  * `run_experiment.py`（訓練）

  * `sweep.py`

  * `eval_metrics.py`（重算 metrics）

  * `index_runs.py`（建 registry）

  * `run_backtest.py`（回測）

* `src/`：核心邏輯（config/data/features/labels/splits/env/train/eval/registry/backtest）

* `runs/`：訓練產物（不要手動改舊 runs）

* `backtests/`：回測產物（已在 .gitignore）

* `reports/registry/`：registry csv/json（要 commit）

* GUI Phase 1.5：FastAPI backend \+ React(Vite) frontend，能讀取 registry/runs/backtests 並呈現（Dashboard/Registry/Runs/Backtests）

---

### **2\) Milestone 1 目標（最小可交付）**

在 GUI 上新增「**可觸發任務**」能力，範圍只包含以下三個動作：  
 A. 觸發訓練：等同執行

* `python -m scripts.run_experiment --config <path> [--set ...]`  
   B. 觸發回測：等同執行

* `python -m scripts.run_backtest --config <path> [--ticker/--tickers] [--start] [--end] [--set ...]`  
   C. 觸發重算評估：等同執行

* `python -m scripts.eval_metrics --run-dir runs/<run_id> [--mode base|finetune] [--model ...]`

**核心要求：**

1. 後端提供 Job API：能建立 job、查 job 狀態、取得 job log（stdout/stderr）。

2. Job 在本機背景執行（可用 `subprocess.Popen`），並將 log 持久化到 `reports/jobs/`（這個資料夾要 commit；log 檔可視需求決定是否 gitignore，但建議 commit job metadata，不一定 commit log）。

3. 前端新增「Jobs」頁（或在 Dashboard 上加區塊也行）：

   * 列出最近 job（id、type、status、start/end time、args）

   * 點進去可看 log（滾動、可複製）

4. 在既有頁面加最小入口：

   * Registry best card：增加「Backtest」按鈕（已存在）旁邊再加「Run Backtest with this model」（若已存在就沿用，否則補）

   * Runs detail：增加「Recompute Metrics」按鈕

   * 另外提供一個簡單表單頁（例如 `/actions`）讓使用者輸入 config path \+ overrides 來觸發 train/backtest（先不做複雜表單）

5. 安全性：避免任意路徑注入

   * config path / run-dir 必須限制在 repo 內（用 `Path.resolve()` \+ 前綴檢查）

   * command 必須是白名單（只能跑上述三個 scripts module），不可讓使用者輸入任意 command。

---

### **3\) 後端具體規格（FastAPI）**

新增模組：

* `api/routes/jobs.py`

* `api/services/jobs.py`

* `api/schemas/jobs.py`

#### **3.1 Job 資料結構（Pydantic）**

`Job` 最少包含：

* `job_id: str`（例如 `job_YYYYMMDD_HHMMSS__<hash8>`）

* `job_type: Literal["train","backtest","eval_metrics"]`

* `status: Literal["QUEUED","RUNNING","SUCCESS","FAILED"]`

* `created_at, started_at, ended_at: Optional[str ISO]`

* `command: List[str]`（實際執行的 argv）

* `cwd: str`

* `artifacts_hint: Optional[dict]`

  * train：可能回傳 `run_id`（如果能從 stdout 解析到）

  * backtest：可能回傳 `bt_run_id`

  * eval\_metrics：回傳 `run_id`

* `log_path: str`（repo 相對路徑，放在 `reports/jobs/<job_id>.log`）

* `meta_path: str`（`reports/jobs/<job_id>.json`）

#### **3.2 API endpoints**

* `POST /api/jobs/train` body:

  * `config_path: str`

  * `overrides: List[str] = []`（對應 `--set key=value` 的字串陣列）

  * `dry_run: bool = False`

* `POST /api/jobs/backtest` body:

  * `config_path: str`

  * `tickers: Optional[List[str]]`

  * `start: Optional[str YYYY-MM-DD]`

  * `end: Optional[str YYYY-MM-DD]`

  * `overrides: List[str] = []`

  * `dry_run: bool = False`

* `POST /api/jobs/eval-metrics` body:

  * `run_id: str`（或 `run_dir: str` 二選一；你決定一種但要一致）

  * `mode: Literal["base","finetune"] = "finetune"`

  * `dry_run: bool = False`

* `GET /api/jobs/recent?limit=50`

* `GET /api/jobs/{job_id}`

* `GET /api/jobs/{job_id}/log`（回傳純文字，或分頁）

#### **3.3 Job 執行**

* 使用 `subprocess.Popen` \+ 將 stdout/stderr 合併寫入 log 檔

* 以 thread 或簡單輪詢方式更新 status（不需要 celery/redis）

* 狀態與 metadata 落地到 `reports/jobs/<job_id>.json`

* 如果程式輸出包含 run\_id/bt\_run\_id（例如 `run_id: ...` / `bt_run_id = ...`），請用 regex 擷取寫入 `artifacts_hint`，讓 UI 可以一鍵跳轉到 Runs/Backtests detail。

---

### **4\) 前端具體規格（React）**

新增頁面與元件：

* `JobsPage`：table 列表（job\_id、type、status、start/end、快捷跳轉）

* `JobDetailPage`：

  * 顯示 metadata（command、cwd、status、artifacts\_hint）

  * log viewer（monospace、可捲動、支援 copy）

* 在 Dashboard 加一個「Recent Jobs」區塊（可點 View All）

在下列頁面加按鈕：

* Run Detail：`Recompute Metrics`（呼叫 POST /api/jobs/eval-metrics）

* Backtests list 或 Registry：提供「Run Backtest」入口（用既有 best model 的 ticker \+ config 預設即可；若 UI 不想選 config，先固定 `configs/backtest/base.yaml`，後續 milestone 再做可選）

UX 最小要求：

* 送出 job 後 toast 顯示 job\_id

* Job list 自動 refresh（每 3\~5 秒輪詢一次即可）

* status 用顏色 badge

---

### **5\) 文件（README）**

更新 README 增加一節「GUI Phase 2 \- Jobs」

* 如何啟動後端、前端

* 如何在 UI 觸發 train/backtest/eval

* Job artifact hint（run\_id / bt\_run\_id）如何跳轉

---

### **6\) 驗證方式（你完成後我會照這些測）**

1. 後端：

* `uvicorn api.app:app --reload --port 8000`

* `curl http://127.0.0.1:8000/api/jobs/recent`

2. 建立一個 dry-run 訓練 job：

* 透過 API 或 UI：config=`configs/base.yaml`, dry\_run=true

* 應產生 `reports/jobs/<job_id>.json` \+ `.log`

3. 建立回測 job（dry-run 或真跑都可）：

* ticker=TSM, config=`configs/backtest/base.yaml`, start/end 可省略

4. UI：

* Jobs 列表可看到剛才的 job

* 點進 detail 可看到 log

---

### **7\) 交付要求**

* 提交所有變更到 `phase2-m1` 分支

* 提供變更檔案清單

* 提供我可直接複製執行的啟動與測試指令

