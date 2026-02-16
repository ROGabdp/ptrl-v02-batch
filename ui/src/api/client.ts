import {
    RegistryBestModel,
    RegistryModelRow,
    RunSummary,
    BacktestSummary,
    RunDetail,
    BacktestDetail,
    EquityPoint
} from '@/types/api';

const API_BASE = '/api';

async function fetchJson<T>(url: string): Promise<T> {
    const response = await fetch(url);
    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API Error ${response.status}: ${errorText}`);
    }
    return response.json();
}

export const api = {
    registry: {
        getBest: () => fetchJson<RegistryBestModel[]>(`${API_BASE}/registry/best`),
        getModels: (params?: { ticker?: string, limit?: number, offset?: number }) => {
            const qs = new URLSearchParams();
            if (params?.ticker) qs.append('ticker', params.ticker);
            if (params?.limit) qs.append('limit', params.limit.toString());
            if (params?.offset) qs.append('offset', params.offset.toString());
            return fetchJson<RegistryModelRow[]>(`${API_BASE}/registry/models?${qs.toString()}`);
        }
    },
    runs: {
        getRecent: (limit = 30) => fetchJson<RunSummary[]>(`${API_BASE}/runs/recent?limit=${limit}`),
        getDetail: (runId: string) => fetchJson<RunDetail>(`${API_BASE}/runs/${runId}`)
    },
    backtests: {
        getRecent: (limit = 30) => fetchJson<BacktestSummary[]>(`${API_BASE}/backtests/recent?limit=${limit}`),
        getDetail: (btId: string) => fetchJson<BacktestDetail>(`${API_BASE}/backtests/${btId}`),
        getEquity: (btId: string) => fetchJson<EquityPoint[]>(`${API_BASE}/backtests/${btId}/equity`)
    }
};
