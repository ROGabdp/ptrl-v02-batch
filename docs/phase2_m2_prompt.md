# Phase 2 — Milestone 2 Prompt (phase2-m2)

## Context / Current State (必讀)

你正在修改 repo：`ptrl-v02-batch`。目前已完成 phase2-m1，具備：

* FastAPI 後端（read \+ jobs trigger）  
* React 前端（Dashboard/Registry/Runs/Backtests/Jobs/Actions 等 9 routes）  
* Jobs 已支援 `train/backtest/eval-metrics`，並落地 `reports/jobs/runtime/`

本 Milestone 2 目標：**把 Jobs 做到可靠可用（增量 log \+ 錯誤顯示 \+ artifacts 串接）、把 Registry 做成可決策（server-side filter/sort \+ 同 ticker compare）、把 Actions 做到少手填（跨頁預填 \+ overrides preview）**。

---

## Branch / Git Rules

1. **從 main 切新分支**（不要在 phase2-m1 上直接做）：  
     
   * `git checkout main`  
   * `git pull`  
   * `git checkout -b phase2-m2`

   

2. 所有 job runtime 檔案仍維持在 `reports/jobs/runtime/` 並被 `.gitignore` 忽略，不得改回版控。  
     
3. commit 建議拆 2\~3 個（Jobs / Registry / Actions），訊息用 `feat(gui): ...` / `feat(api): ...`。

---

# Deliverables

## (A) Jobs API：增量 Log \+ 統一 schema \+ 可靠 artifacts

### A1. API 變更清單

修改/新增檔案（依你目前結構微調，保持一致）：

* `api/routes/jobs.py` (MODIFY)  
* `api/schemas/jobs.py` (MODIFY)  
* `api/services/jobs.py` (MODIFY)  
* `api/services/readers.py` (OPTIONAL, 可新增共用讀檔)  
* `README.md` (MODIFY：補 Jobs log 增量與狀態欄位說明)

### A2. `/api/jobs/{job_id}/log` 支援 bytes offset（核心）

**需求：避免 UI 每次輪詢整包 log。**

#### Endpoint

`GET /api/jobs/{job_id}/log?offset=0&tail=20000`

#### Query params

* `offset: int = 0`  
    
  * 從 log 檔案的 byte offset 開始讀取


* `tail: int = 20000`  
    
  * 若 `offset == 0` 且檔案很大，預設只回最後 `tail` bytes（避免初次載入爆量）

#### Response schema（新增 Pydantic）

`JobLogResponse`

{

  "job\_id": "job\_...",

  "content": "....",

  "next\_offset": 12345,

  "is\_truncated": true,

  "log\_path": "reports/jobs/runtime/....log"

}

規則：

* 若 `offset > 0`：從 `offset` 讀到 EOF，`is_truncated=false`。  
* 若 `offset == 0` 且檔案 \> tail：只回最後 tail bytes，`is_truncated=true`，`next_offset` 仍需是 EOF offset（或 tail 起點 \+ len(content) 也可，但要一貫）。  
* 內容讀取用二進位 bytes \+ decode（utf-8 errors="replace"）。  
* 若檔案不存在：回 404，包含清楚訊息。

### A3. `GET /api/jobs/{job_id}` schema 補齊（UI 需要）

`JobDetailResponse` 至少包含以下欄位（缺一不可）：

* `job_id: str`  
* `job_type: "train" | "backtest" | "eval-metrics"`  
* `status: "QUEUED" | "RUNNING" | "SUCCESS" | "FAILED"`  
* `created_at: str` (ISO)  
* `started_at?: str`  
* `ended_at?: str`  
* `duration_sec?: float`（後端算）  
* `exit_code?: int`（成功 0；失敗非 0；未完成 null）  
* `error_message?: str`（FAILED 時提供，從 stderr 或 exception 摘要）  
* `cwd: str`  
* `command: list[str]`（不要只給 string）  
* `args_preview: str`（長 command 做短字串，UI 用）  
* `artifacts: { run_id?, run_dir?, bt_run_id?, bt_dir? }`  
* `runtime: { meta_path: str, log_path: str }`（讓 UI/debug 方便）

#### artifacts 解析規則（MODIFY jobs service）

* train：解析 stdout 中 `run_id:` `run_dir:`（已做，但確保寫入 `artifacts` 結構）  
* backtest：解析 stdout 中 `bt_run_id:` 或 `bt_run_id =` / `out_dir:`（視你 scripts.run\_backtest 的輸出格式）  
* eval-metrics：解析 run\_id（如果 stdout 有），或至少留下 `artifacts_parse_error`

**要求：解析失敗不要沉默，寫 `artifacts_parse_error` 供 debug。**

### A4. `GET /api/jobs/recent` 支援 filter（選做但推薦）

新增 query params（server-side filter \+ UI 使用）：

* `status?: str`  
* `job_type?: str`  
* `limit: int = 100`

---

## (B) UI：Jobs 改成增量 log viewer \+ 更清楚的失敗資訊

### B1. 檔案修改清單

* `ui/src/api/client.ts` (MODIFY)  
    
* `ui/src/types/api.ts` (MODIFY)  
    
* `ui/src/pages/Jobs.tsx` (MODIFY)  
    
* `ui/src/pages/JobDetail.tsx` (MODIFY)  
    
* `ui/src/components/` 新增：  
    
  * `LogViewer.tsx` (NEW)  
  * `StatusBadge.tsx` (OPTIONAL, 若你已有就沿用)

### B2. 型別新增/更新

在 `ui/src/types/api.ts` 加：

* `JobLogResponse`  
* 更新 `JobDetail` type：對齊後端 schema（含 `error_message/exit_code/artifacts/runtime/command[]`）

### B3. `LogViewer` 元件（核心）

需求：

* 以 bytes offset 方式增量抓 log  
* 支援 Auto-follow（預設開啟）  
* 支援 Copy log（整份或可視範圍）

行為：

* 初次載入：GET `/api/jobs/{id}/log?offset=0&tail=20000`  
* 之後輪詢：用 `next_offset`，GET `/log?offset=<next_offset>`  
* 若回傳 content 空字串也要更新 offset（避免卡住）  
* Auto-follow 開啟時，log 更新會自動 scroll 到最底

UI：

* 開關：`Auto-follow` toggle（右上）  
* 按鈕：`Copy`（copy 全文）  
* 顯示：深色 monospace 區塊，`white-space: pre-wrap`，高度 520px scroll

### B4. JobDetail 頁改善

* 在頁面上方新增「Error Summary」（只在 FAILED 顯示）：  
    
  * `StatusBadge(FAILED)`  
  * `exit_code`  
  * `error_message`（可折疊）


* artifacts 區塊：如果有 `run_id` / `bt_run_id`，給明確 CTA 按鈕：  
    
  * `View Run`  
  * `View Backtest`

---

## (C) Registry 決策化：server-side filter/sort \+ 同 ticker compare drawer

### C1. Backend：`/api/registry/models` 支援 filter/sort/paging

修改檔案：

* `api/routes/registry.py` (MODIFY)  
* `api/services/readers.py` or registry reader (MODIFY/NEW)  
* `api/schemas/registry.py` (若有；否則新增 schema)

#### Endpoint

`GET /api/registry/models`

#### Query params（必做）

* `ticker?: str`  
    
* `min_lift?: float`  
    
* `min_precision?: float`  
    
* `min_support?: int`  
    
* `max_buy_rate?: float`（可選，預設 None）  
    
* `sort?: str`  
    
  * 預設：`precision_desc,lift_desc,buy_rate_asc,support_desc`


* `limit: int = 50`  
    
* `offset: int = 0`

#### Response

{

  "items": \[ ...RegistryModelRow... \],

  "total": 123,

  "limit": 50,

  "offset": 0

}

#### RegistryModelRow 欄位（UI/比較需要）

確保 items 內每列至少有：

* `ticker, run_id, mode`  
* `label_horizon_days, label_threshold`  
* `precision, recall, f1, accuracy`  
* `buy_rate, positive_rate, lift`  
* `tp, fp, tn, fn, support`  
* `model_final_path, config_path, metrics_path, manifest_path`  
* `start_time, end_time, status`

注意：現在 UI 有些欄位是從 CSV 顯示，請確保欄位名稱一致，避免 UI mapping 混亂。

### C2. Frontend：Registry 改成 server-side filter/sort/paging

修改：

* `ui/src/pages/Registry.tsx` (MODIFY)  
* `ui/src/api/client.ts` (MODIFY)  
* `ui/src/components/CompareDrawer.tsx` (NEW)

#### Filter Bar UI 元件（具體欄位）

* `Ticker` input（string）  
    
* `Min Lift` input（number）  
    
* `Min Precision` input（number）  
    
* `Min Support` input（number，預設 30）  
    
* `Sort` dropdown（預設值固定，不要讓使用者手打）  
    
  * Option 1（default）：Precision↓ Lift↓ BuyRate↑ Support↓  
  * Option 2：Lift↓ Precision↓ BuyRate↑ Support↓  
  * Option 3：Precision↓ Support↓ Lift↓ BuyRate↑


* `Refetch` button

#### Table 欄位（請調整更可讀）

* Ticker  
* Run ID（link）  
* Label (H/TH)：顯示 `120d / 20%`  
* Precision（%）  
* Lift（x）  
* Buy Rate（%）  
* Pos Rate（%）  
* Support  
* TP/FP（顯示 `tp / fp`，hover 顯示 tn/fn）  
* Actions：`Details`、`Run Backtest`

#### 同 ticker compare（最小版）

行為：

* table 每列加 checkbox  
* 限制：**只能勾同 ticker**，若勾到不同 ticker，UI 顯示提示並拒絕  
* 右上顯示 Compare(N) button → 打開 Drawer Drawer 內容（表格即可）：  
* run\_id  
* label(H/TH)  
* precision / lift / buy\_rate / positive\_rate / support  
* tp/fp/tn/fn

---

## (D) Actions：跨頁預填 \+ overrides preview（減少手填）

### D1. Frontend：Actions 支援 querystring 預填

修改：

* `ui/src/pages/Actions.tsx` (MODIFY)

支援 URL：

* `/actions?type=backtest&ticker=TSM&model_path=...&start=YYYY-MM-DD&end=YYYY-MM-DD`  
* `/actions?type=train&config_path=configs/base.yaml`  
* `/actions?type=eval&run_id=...`（可選）

要求：

* 讀取 querystring 後自動填入表單欄位  
* `type` 會自動切換到對應 form tab（train/backtest）

### D2. Overrides preview（避免打錯）

在送出前顯示「Parsed Overrides Preview」：

* textarea 每行 `key=value`  
* parse 成 dict（忽略空行、`#` 開頭註解）  
* preview 顯示 JSON（可 copy）

### D3. 跨頁帶入入口（改 UI buttons）

修改：

* `ui/src/pages/Dashboard.tsx`  
    
* `ui/src/pages/Registry.tsx`  
    
* `ui/src/pages/RunDetail.tsx`（可選） 行為：  
    
* `Run Backtest` 不要直接 POST job（或保留也可），新增一個：  
    
  * `Open in Actions`：導到 `/actions?type=backtest&ticker=...&model_path=...`

---

# Verification / Acceptance Criteria（必做驗收指令）

## 1\) Backend 快速驗收

\# 1\) 啟動

uvicorn api.app:app \--reload \--port 8000

\# 2\) Jobs recent

curl http://127.0.0.1:8000/api/jobs/recent?limit=5

\# 3\) 觸發一個 dry-run job

curl \-X POST http://127.0.0.1:8000/api/jobs/backtest \-H "Content-Type: application/json" \-d "{\\"config\_path\\":\\"configs/backtest/base.yaml\\",\\"tickers\\":\[\\"TSM\\"\],\\"dry\_run\\":true}"

\# 4\) 取 job\_id 後測 log tail \+ offset

curl "http://127.0.0.1:8000/api/jobs/\<JOB\_ID\>/log?offset=0\&tail=20000"

curl "http://127.0.0.1:8000/api/jobs/\<JOB\_ID\>/log?offset=\<NEXT\_OFFSET\>"

\# 5\) Registry server-side filter/sort

curl "http://127.0.0.1:8000/api/registry/models?ticker=TSM\&min\_lift=1.1\&min\_precision=0.6\&min\_support=30\&limit=50\&offset=0"

## 2\) Frontend 驗收

cd ui

npm run build

npm run dev

手動驗收項目：

1. JobDetail：log 會增量更新（不閃爍、不整包重載），Auto-follow 正常。  
     
2. Job 失敗時：顯示 error\_message \+ exit\_code（不是只看 log）。  
     
3. Registry：  
     
   * filter bar 改成 server-side（切頁不會讓過濾失效）  
   * sort 預設為 Precision↓ Lift↓ BuyRate↑ Support↓  
   * compare：只能勾同 ticker，Drawer 顯示比較表

   

4. Actions：  
     
   * 透過 `/actions?...` 能正確預填  
   * overrides 有 preview，送出 payload 正確

---

# Non-goals（這個 Milestone 不做）

* 不做 Job cancel/kill  
* 不做多用戶/權限  
* 不做長期任務佇列系統（Celery/RQ）  
* 不做跨 ticker compare（只同 ticker）

---

## Output / What to commit

* 所有新增檔案需納入版控（包含 docs 若有）  
* runtime log/metadata 檔案不得進 git（仍在 `.gitignore`）  
* README 需更新：描述 log offset API、registry filter/sort、actions 預填

