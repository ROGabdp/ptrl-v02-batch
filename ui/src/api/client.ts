import {
    BacktestDetail,
    BacktestJobRequest,
    BacktestSummary,
    EquityPoint,
    EvalMetricsJobRequest,
    JobRecord,
    RegistryBestModel,
    RegistryModelRow,
    RunDetail,
    RunSummary,
    TrainJobRequest,
} from '@/types/api'

const API_BASE = '/api'

async function fetchJson<T>(url: string): Promise<T> {
    const response = await fetch(url)
    if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`API Error ${response.status}: ${errorText}`)
    }
    return response.json()
}

async function postJson<T>(url: string, payload: unknown): Promise<T> {
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    })
    if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`API Error ${response.status}: ${errorText}`)
    }
    return response.json()
}

async function fetchText(url: string): Promise<string> {
    const response = await fetch(url)
    if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`API Error ${response.status}: ${errorText}`)
    }
    return response.text()
}

export const api = {
    registry: {
        getBest: () => fetchJson<RegistryBestModel[]>(`${API_BASE}/registry/best`),
        getModels: (params?: { ticker?: string; limit?: number; offset?: number }) => {
            const qs = new URLSearchParams()
            if (params?.ticker) qs.append('ticker', params.ticker)
            if (params?.limit) qs.append('limit', params.limit.toString())
            if (params?.offset) qs.append('offset', params.offset.toString())
            return fetchJson<RegistryModelRow[]>(`${API_BASE}/registry/models?${qs.toString()}`)
        },
    },
    runs: {
        getRecent: (limit = 30) => fetchJson<RunSummary[]>(`${API_BASE}/runs/recent?limit=${limit}`),
        getDetail: (runId: string) => fetchJson<RunDetail>(`${API_BASE}/runs/${runId}`),
        getCheckpoints: (runId: string, mode: 'base' | 'finetuned', ticker?: string) => {
            const qs = new URLSearchParams({ mode })
            if (ticker) qs.append('ticker', ticker)
            return fetchJson<string[]>(`${API_BASE}/runs/${runId}/checkpoints?${qs.toString()}`)
        },
    },
    backtests: {
        getRecent: (limit = 30) => fetchJson<BacktestSummary[]>(`${API_BASE}/backtests/recent?limit=${limit}`),
        getDetail: (btId: string) => fetchJson<BacktestDetail>(`${API_BASE}/backtests/${btId}`),
        getEquity: (btId: string) => fetchJson<EquityPoint[]>(`${API_BASE}/backtests/${btId}/equity`),
    },
    jobs: {
        createTrain: (payload: TrainJobRequest) => postJson<JobRecord>(`${API_BASE}/jobs/train`, payload),
        createBacktest: (payload: BacktestJobRequest) => postJson<JobRecord>(`${API_BASE}/jobs/backtest`, payload),
        createEvalMetrics: (payload: EvalMetricsJobRequest) =>
            postJson<JobRecord>(`${API_BASE}/jobs/eval-metrics`, payload),
        getRecent: (limit = 50) => fetchJson<JobRecord[]>(`${API_BASE}/jobs/recent?limit=${limit}`),
        getOne: (jobId: string) => fetchJson<JobRecord>(`${API_BASE}/jobs/${jobId}`),
        getLog: (jobId: string) => fetchText(`${API_BASE}/jobs/${jobId}/log`),
    },
}
