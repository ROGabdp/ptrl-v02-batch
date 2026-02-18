import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { DailyConfig, DailyJobItem, JobDetail } from '../types/api'

// Simple helper to format date
const formatDate = (date: Date) => date.toISOString().split('T')[0]

export default function DailyPage() {
    const [config, setConfig] = useState<DailyConfig | null>(null)
    const [loadingConfig, setLoadingConfig] = useState(false)
    const [saving, setSaving] = useState(false)
    const [lastSaved, setLastSaved] = useState<string | null>(null)

    // Run state
    const [dryRun, setDryRun] = useState(false)
    const [overrideStart, setOverrideStart] = useState('')
    const [overrideEnd, setOverrideEnd] = useState('')
    const [running, setRunning] = useState(false)
    const [batchItems, setBatchItems] = useState<DailyJobItem[]>([])

    // Extended status for items (including full job/backtest detail)
    const [itemDetails, setItemDetails] = useState<Record<string, { job?: JobDetail, summary?: string }>>({})

    useEffect(() => {
        const loadConfig = async () => {
            try {
                setLoadingConfig(true)
                const res = await api.daily.getConfig()
                setConfig(res.config)
                if (res.saved_at) setLastSaved(res.saved_at)
            } catch (err: any) {
                console.error(err)
                alert('Failed to load daily config')
            } finally {
                setLoadingConfig(false)
            }
        }
        loadConfig()
    }, [])

    const handleSave = async () => {
        if (!config) return
        try {
            setSaving(true)
            const res = await api.daily.saveConfig(config)
            setConfig(res.config)
            setLastSaved(res.saved_at || new Date().toISOString())
        } catch (err: any) {
            console.error(err)
            alert('Failed to save config')
        } finally {
            setSaving(false)
        }
    }

    const handleRun = async () => {
        try {
            setRunning(true)
            const res = await api.daily.runBatch({
                dry_run: dryRun,
                tickers: config?.tickers, // Use tickers from config (or allow override in UI later)
                date_override: {
                    start: overrideStart || null,
                    end: overrideEnd || null,
                },
            })
            setBatchItems(res.items)
            // Reset details for new run
            setItemDetails({})
        } catch (err: any) {
            console.error(err)
            alert('Failed to run batch')
        } finally {
            setRunning(false)
        }
    }

    // Polling logic
    useEffect(() => {
        if (batchItems.length === 0) return

        const unfinished = batchItems.some(item => {
            const detail = itemDetails[item.ticker]?.job
            return !detail || (detail.status !== 'SUCCESS' && detail.status !== 'FAILED')
        })

        if (!unfinished) return

        const interval = setInterval(async () => {
            const updates: Record<string, { job?: JobDetail, summary?: string }> = { ...itemDetails }
            let hasChanges = false

            await Promise.all(batchItems.map(async (item) => {
                const current = updates[item.ticker]?.job
                if (current && (current.status === 'SUCCESS' || current.status === 'FAILED')) return

                try {
                    const job = await api.jobs.getOne(item.job_id)
                    let summary = updates[item.ticker]?.summary

                    // If success, try to fetch backtest summary
                    if (job.status === 'SUCCESS' && job.artifacts?.bt_run_id && !summary) {
                        try {
                            const bt = await api.backtests.getDetail(job.artifacts.bt_run_id)
                            summary = bt.end_date_summary_text || bt.summary_text
                        } catch (e: any) {
                            console.error('Failed to fetch summary', e)
                        }
                    }
                    updates[item.ticker] = { job, summary }
                    hasChanges = true
                } catch (e: any) {
                    console.error('Poll error', e)
                }
            }))

            if (hasChanges) {
                setItemDetails(updates)
            }
        }, 3000)

        return () => clearInterval(interval)
    }, [batchItems, itemDetails])

    // Render Helpers
    if (loadingConfig && !config) return <div className="p-8">Loading...</div>
    if (!config) return <div className="p-8">Error loading config</div>

    const resolvedEndPreview = overrideEnd ? overrideEnd : (overrideStart ? `Today (${formatDate(new Date())})` : (config.backtest.end || `Today (${formatDate(new Date())})`))

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-8">
            <header className="flex justify-between items-center">
                <h1 className="text-2xl font-bold">Daily Decision Center</h1>
                <div className="text-sm text-gray-500">
                    Last saved: {lastSaved ? new Date(lastSaved).toLocaleString() : 'Never'}
                </div>
            </header>

            {/* Config Editor */}
            <section className="bg-white p-6 rounded shadow space-y-6">
                <h2 className="text-xl font-semibold border-b pb-2">Configuration</h2>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* General Settings */}
                    <div className="space-y-4">
                        <label className="block">
                            <span className="text-sm font-bold">Tickers</span>
                            <input
                                className="mt-1 block w-full border rounded p-2"
                                value={config.tickers.join(', ')}
                                onChange={e => setConfig({ ...config, tickers: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })}
                            />
                        </label>

                        <div className="grid grid-cols-2 gap-4">
                            <label className="block">
                                <span className="text-sm font-bold">Start Date</span>
                                <input
                                    type="date"
                                    className="mt-1 block w-full border rounded p-2"
                                    value={config.backtest.start || ''}
                                    onChange={e => setConfig({ ...config, backtest: { ...config.backtest, start: e.target.value } })}
                                />
                            </label>
                            <label className="block">
                                <span className="text-sm font-bold">End Date</span>
                                <input
                                    type="date"
                                    className="mt-1 block w-full border rounded p-2"
                                    value={config.backtest.end || ''}
                                    onChange={e => setConfig({ ...config, backtest: { ...config.backtest, end: e.target.value } })}
                                />
                            </label>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <label className="block">
                                <span className="text-sm font-bold">Initial Cash</span>
                                <input
                                    type="number"
                                    className="mt-1 block w-full border rounded p-2"
                                    value={config.backtest.initial_cash}
                                    onChange={e => setConfig({ ...config, backtest: { ...config.backtest, initial_cash: Number(e.target.value) } })}
                                />
                            </label>
                            <label className="block">
                                <span className="text-sm font-bold">Benchmark</span>
                                <input
                                    className="mt-1 block w-full border rounded p-2"
                                    value={config.backtest.benchmark}
                                    onChange={e => setConfig({ ...config, backtest: { ...config.backtest, benchmark: e.target.value } })}
                                />
                            </label>
                        </div>
                    </div>

                    {/* Exit Strategy Defaults */}
                    <div className="space-y-4">
                        <h3 className="font-bold text-gray-700">Default Exit Strategy</h3>
                        <div className="grid grid-cols-2 gap-4">
                            <label className="block">
                                <span className="text-sm">Stop Loss % (Positive)</span>
                                <input
                                    type="number" step="0.01"
                                    className="mt-1 block w-full border rounded p-2"
                                    value={config.strategy.exit?.stop_loss_pct ?? 0}
                                    onChange={e => {
                                        const val = Number(e.target.value)
                                        setConfig({ ...config, strategy: { ...config.strategy, exit: { ...config.strategy.exit!, stop_loss_pct: val } } })
                                    }}
                                />
                            </label>
                            <label className="block">
                                <span className="text-sm">Take Profit Activation %</span>
                                <input
                                    type="number" step="0.01"
                                    className="mt-1 block w-full border rounded p-2"
                                    value={config.strategy.exit?.take_profit_activation_pct ?? 0}
                                    onChange={e => {
                                        const val = Number(e.target.value)
                                        setConfig({ ...config, strategy: { ...config.strategy, exit: { ...config.strategy.exit!, take_profit_activation_pct: val } } })
                                    }}
                                />
                            </label>
                            <label className="block">
                                <span className="text-sm">Trail Stop Low %</span>
                                <input
                                    type="number" step="0.01"
                                    className="mt-1 block w-full border rounded p-2"
                                    value={config.strategy.exit?.trail_stop_low_pct ?? 0}
                                    onChange={e => {
                                        const val = Number(e.target.value)
                                        setConfig({ ...config, strategy: { ...config.strategy, exit: { ...config.strategy.exit!, trail_stop_low_pct: val } } })
                                    }}
                                />
                            </label>
                            <label className="block">
                                <span className="text-sm">Trail Stop High %</span>
                                <input
                                    type="number" step="0.01"
                                    className="mt-1 block w-full border rounded p-2"
                                    value={config.strategy.exit?.trail_stop_high_pct ?? 0}
                                    onChange={e => {
                                        const val = Number(e.target.value)
                                        setConfig({ ...config, strategy: { ...config.strategy, exit: { ...config.strategy.exit!, trail_stop_high_pct: val } } })
                                    }}
                                />
                            </label>
                            <label className="block">
                                <span className="text-sm">High Profit Threshold %</span>
                                <input
                                    type="number" step="0.01"
                                    className="mt-1 block w-full border rounded p-2"
                                    value={config.strategy.exit?.high_profit_threshold_pct ?? 0}
                                    onChange={e => {
                                        const val = Number(e.target.value)
                                        setConfig({ ...config, strategy: { ...config.strategy, exit: { ...config.strategy.exit!, high_profit_threshold_pct: val } } })
                                    }}
                                />
                            </label>
                        </div>
                    </div>
                </div>

                {/* Confirm Thresholds List */}
                <div className="space-y-2">
                    <h3 className="font-bold text-gray-700">Entry Thresholds</h3>
                    <div className="space-y-2">
                        {config.strategy.entry?.conf_thresholds.map((th, idx) => (
                            <div key={idx} className="flex gap-4 items-center">
                                <input
                                    type="number" step="0.01" placeholder="Min Conf"
                                    className="border rounded p-1 w-32"
                                    value={th.min_conf}
                                    onChange={e => {
                                        const newThs = [...(config.strategy.entry?.conf_thresholds || [])]
                                        newThs[idx].min_conf = Number(e.target.value)
                                        setConfig({ ...config, strategy: { ...config.strategy, entry: { ...config.strategy.entry!, conf_thresholds: newThs } } })
                                    }}
                                />
                                <span className="text-gray-500">Min Conf</span>
                                <input
                                    type="number" step="0.01" placeholder="Buy Frac"
                                    className="border rounded p-1 w-32"
                                    value={th.buy_frac}
                                    onChange={e => {
                                        const newThs = [...(config.strategy.entry?.conf_thresholds || [])]
                                        newThs[idx].buy_frac = Number(e.target.value)
                                        setConfig({ ...config, strategy: { ...config.strategy, entry: { ...config.strategy.entry!, conf_thresholds: newThs } } })
                                    }}
                                />
                                <span className="text-gray-500">Buy Frac</span>
                                <button
                                    className="text-red-500 hover:text-red-700 px-2"
                                    onClick={() => {
                                        const newThs = config.strategy.entry?.conf_thresholds.filter((_, i) => i !== idx) || []
                                        setConfig({ ...config, strategy: { ...config.strategy, entry: { ...config.strategy.entry!, conf_thresholds: newThs } } })
                                    }}
                                >
                                    Remove
                                </button>
                            </div>
                        ))}
                        <button
                            className="bg-gray-100 px-3 py-1 rounded text-sm hover:bg-gray-200"
                            onClick={() => {
                                const newThs = [...(config.strategy.entry?.conf_thresholds || []), { min_conf: 0.9, buy_frac: 0.1 }]
                                setConfig({ ...config, strategy: { ...config.strategy, entry: { ...config.strategy.entry!, conf_thresholds: newThs } } })
                            }}
                        >
                            + Add Threshold
                        </button>
                    </div>
                </div>

                <div className="flex justify-end">
                    <button
                        className={`bg-blue-600 text-white px-6 py-2 rounded shadow hover:bg-blue-700 disabled:opacity-50`}
                        onClick={handleSave}
                        disabled={saving}
                    >
                        {saving ? 'Saving...' : 'Save Configuration'}
                    </button>
                </div>
            </section>

            {/* Run Panel */}
            <section className="bg-white p-6 rounded shadow space-y-4 border-l-4 border-green-500">
                <h2 className="text-xl font-semibold">Run Backtests</h2>
                <div className="flex flex-wrap items-end gap-6">
                    <label className="block">
                        <span className="text-sm font-bold text-gray-700">Override Start</span>
                        <input
                            type="date"
                            className="mt-1 block border rounded p-2"
                            value={overrideStart}
                            onChange={e => setOverrideStart(e.target.value)}
                        />
                    </label>
                    <label className="block">
                        <span className="text-sm font-bold text-gray-700">Override End (Empty = Today)</span>
                        <input
                            type="date"
                            className="mt-1 block border rounded p-2"
                            value={overrideEnd}
                            onChange={e => setOverrideEnd(e.target.value)}
                            placeholder="yyyy-mm-dd"
                        />
                    </label>
                    <div className="flex items-center h-10 pb-1">
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={dryRun}
                                onChange={e => setDryRun(e.target.checked)}
                            />
                            <span>Dry Run</span>
                        </label>
                    </div>
                </div>

                <div className="bg-gray-50 p-2 rounded text-sm text-gray-600">
                    Will run backtests from <strong>{overrideStart || config.backtest.start}</strong> to <strong>{resolvedEndPreview}</strong>
                </div>

                <div className="flex gap-4">
                    <button
                        className="bg-green-600 text-white px-8 py-3 rounded shadow hover:bg-green-700 text-lg font-bold disabled:opacity-50"
                        onClick={handleRun}
                        disabled={running}
                    >
                        {running ? 'Starting...' : 'Run All Backtests'}
                    </button>
                </div>
            </section>

            {/* Results Panel */}
            {batchItems.length > 0 && (
                <section className="space-y-4">
                    <h2 className="text-xl font-semibold">Results</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {batchItems.map(item => {
                            const detail = itemDetails[item.ticker]
                            const job = detail?.job
                            const summary = detail?.summary
                            const status = job?.status || 'QUEUED'

                            let statusColor = 'bg-gray-200'
                            if (status === 'RUNNING') statusColor = 'bg-blue-100 text-blue-800'
                            if (status === 'SUCCESS') statusColor = 'bg-green-100 text-green-800'
                            if (status === 'FAILED') statusColor = 'bg-red-100 text-red-800'

                            return (
                                <div key={item.ticker} className="bg-white rounded shadow p-4 border flex flex-col gap-3">
                                    <div className="flex justify-between items-center">
                                        <h3 className="font-bold text-lg">{item.ticker}</h3>
                                        <span className={`px-2 py-1 rounded text-xs font-bold ${statusColor}`}>
                                            {status}
                                        </span>
                                    </div>

                                    <div className="text-sm space-y-1">
                                        <div>
                                            Job ID: <a href={item.job_url} target="_blank" className="text-blue-600 hover:underline">{item.job_id}</a>
                                        </div>
                                        {job?.artifacts?.bt_run_id && (
                                            <div>
                                                Backtest: <a href={`/backtests/${job.artifacts.bt_run_id}`} target="_blank" className="text-blue-600 hover:underline">{job.artifacts.bt_run_id}</a>
                                            </div>
                                        )}
                                    </div>

                                    {status === 'FAILED' && job?.error_message && (
                                        <div className="text-xs text-red-600 bg-red-50 p-2 rounded max-h-32 overflow-auto font-mono">
                                            {job.error_message}
                                        </div>
                                    )}

                                    {status === 'SUCCESS' && summary && (
                                        <div className="mt-2">
                                            <div className="text-xs font-semibold text-gray-500 mb-1">End Date Summary</div>
                                            <pre className="text-xs bg-gray-900 text-green-400 p-2 rounded overflow-auto h-48 select-all whitespace-pre-wrap">
                                                {summary}
                                            </pre>
                                        </div>
                                    )}
                                </div>
                            )
                        })}
                    </div>
                </section>
            )}
        </div>
    )
}
