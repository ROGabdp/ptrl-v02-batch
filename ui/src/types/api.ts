export interface RegistryBestModel {
    ticker: string
    run_id: string
    model_path: string
    model_type: string
    precision: number
    lift: number
    buy_rate: number
    label_horizon_days: number
    label_threshold: number
}

export interface RegistryModelRow {
    ticker: string
    run_id: string
    model_path: string
    precision: number
    lift: number
    buy_rate: number
    tp: number
    fp: number
}

export interface RunSummary {
    run_id: string
    tickers: string[]
    start_time: string | null
    end_time: string | null
    status: string
    manifest_path: string
}

export interface BacktestSummary {
    bt_run_id: string
    ticker: string
    model_path: string
    start_date: string
    end_date: string
    total_return: number
    cagr: number
    max_drawdown: number
    win_rate: number
    trade_count: number
    timestamp: string | null
}

export interface EquityPoint {
    date: string
    portfolio_value: number
    benchmark_value?: number
    injected_cash?: number
}

export interface BacktestDetail {
    bt_run_id: string
    ticker: string
    config: any
    metrics: any
    summary_text: string
    end_date_summary_text: string | null
    trades: any[]
    equity_curve: EquityPoint[]
    plot_path: string | null
}

export interface RunDetail {
    run_id: string
    config: any
    metrics: any
    manifest: any
    models: {
        base: string[]
        finetuned: Record<string, string[]>
    }
}
