import {
    BacktestDetail,
    BacktestJobRequest,
    BacktestSummary,
    EquityPoint,
    EvalMetricsJobRequest,
    JobDetail,
    JobLogResponse,
    RegistryBestModel,
    RegistryModelsResponse,
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

export const api = {
    registry: {
        getBest: () => fetchJson<RegistryBestModel[]>(`${API_BASE}/registry/best`),
        getModels: (params?: {
            ticker?: string
            min_lift?: number
            min_precision?: number
            min_support?: number
            max_buy_rate?: number
            sort?: string
            limit?: number
            offset?: number
        }) => {
            const qs = new URLSearchParams()
            if (params?.ticker) qs.append('ticker', params.ticker)
            if (params?.min_lift !== undefined) qs.append('min_lift', params.min_lift.toString())
            if (params?.min_precision !== undefined) qs.append('min_precision', params.min_precision.toString())
            if (params?.min_support !== undefined) qs.append('min_support', params.min_support.toString())
            if (params?.max_buy_rate !== undefined) qs.append('max_buy_rate', params.max_buy_rate.toString())
            if (params?.sort) qs.append('sort', params.sort)
            if (params?.limit) qs.append('limit', params.limit.toString())
            if (params?.offset !== undefined) qs.append('offset', params.offset.toString())
            return fetchJson<RegistryModelsResponse>(`${API_BASE}/registry/models?${qs.toString()}`)
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
        createTrain: (payload: TrainJobRequest) => postJson<JobDetail>(`${API_BASE}/jobs/train`, payload),
        createBacktest: (payload: BacktestJobRequest) => postJson<JobDetail>(`${API_BASE}/jobs/backtest`, payload),
        createEvalMetrics: (payload: EvalMetricsJobRequest) =>
            postJson<JobDetail>(`${API_BASE}/jobs/eval-metrics`, payload),
        getRecent: (params?: { limit?: number; status?: string; job_type?: string }) => {
            const qs = new URLSearchParams()
            qs.append('limit', String(params?.limit ?? 100))
            if (params?.status) qs.append('status', params.status)
            if (params?.job_type) qs.append('job_type', params.job_type)
            return fetchJson<JobDetail[]>(`${API_BASE}/jobs/recent?${qs.toString()}`)
        },
        getOne: (jobId: string) => fetchJson<JobDetail>(`${API_BASE}/jobs/${jobId}`),
        getLog: (jobId: string, params?: { offset?: number; tail?: number }) => {
            const qs = new URLSearchParams()
            if (params?.offset !== undefined) qs.append('offset', String(params.offset))
            if (params?.tail !== undefined) qs.append('tail', String(params.tail))
            return fetchJson<JobLogResponse>(`${API_BASE}/jobs/${jobId}/log?${qs.toString()}`)
        },
    },
}