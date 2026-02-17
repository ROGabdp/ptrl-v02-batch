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
    positive_rate?: number
    tp?: number
    fp?: number
    support?: number
}

export interface RegistryModelRow {
    ticker: string
    run_id: string
    mode?: string
    label_horizon_days?: number
    label_threshold?: number
    precision?: number
    recall?: number
    f1?: number
    accuracy?: number
    buy_rate?: number
    positive_rate?: number
    lift?: number
    tp?: number
    fp?: number
    tn?: number
    fn?: number
    support?: number
    model_final_path?: string
    config_path?: string
    metrics_path?: string
    manifest_path?: string
    start_time?: string
    end_time?: string
    status?: string
}

export interface RegistryModelsResponse {
    items: RegistryModelRow[]
    total: number
    limit: number
    offset: number
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
    strategy_summary?: {
        stop_loss_pct?: number
        take_profit_activation_pct?: number
        trail_stop_low_pct?: number
        trail_stop_high_pct?: number
        min_days_between_entries?: number
        use_market_filter?: boolean
        conf_thresholds?: number[]
    }
    recent_trades?: {
        entry_date: string
        exit_date: string
        pnl_pct: number
        exit_reason: string
        holding_days: number
    }[]
    mdd_window?: {
        mdd_peak_date: string
        mdd_trough_date: string
        mdd_recovery_date: string | null
    }
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
    checkpoints_count: number
    checkpoints_sample: string[]
}

export type JobType = 'train' | 'backtest' | 'eval-metrics' | 'eval_metrics'
export type JobStatus = 'QUEUED' | 'RUNNING' | 'SUCCESS' | 'FAILED'

export interface JobArtifacts {
    run_id?: string
    run_dir?: string
    bt_run_id?: string
    bt_dir?: string
    artifacts_parse_error?: string
}

export interface JobRuntimePaths {
    meta_path: string
    log_path: string
}

export interface JobDetail {
    job_id: string
    job_type: JobType
    status: JobStatus
    created_at: string
    started_at: string | null
    ended_at: string | null
    duration_sec?: number | null
    exit_code?: number | null
    error_message?: string | null
    command: string[]
    args_preview: string
    cwd: string
    artifacts: JobArtifacts
    runtime: JobRuntimePaths
}

export interface JobLogResponse {
    job_id: string
    content: string
    next_offset: number
    is_truncated: boolean
    log_path: string
}

export type JobRecord = JobDetail

export interface TrainJobRequest {
    config_path: string
    overrides?: string[]
    dry_run?: boolean
}

export interface BacktestJobRequest {
    config_path: string
    tickers?: string[]
    model_path?: string
    start?: string
    end?: string
    overrides?: string[]
    dry_run?: boolean
}

export interface EvalMetricsJobRequest {
    run_id: string
    mode?: 'base' | 'finetune'
    dry_run?: boolean
}