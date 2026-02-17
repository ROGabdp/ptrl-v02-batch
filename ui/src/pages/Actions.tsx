import { FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/api/client'
import { JobRecord } from '@/types/api'

function parseOverrides(raw: string): string[] {
    return raw
        .split('\n')
        .map((x) => x.trim())
        .filter(Boolean)
}

function parseTickers(raw: string): string[] {
    return raw
        .split(',')
        .map((x) => x.trim().toUpperCase())
        .filter(Boolean)
}

export default function Actions() {
    const [trainConfig, setTrainConfig] = useState('configs/base.yaml')
    const [trainOverrides, setTrainOverrides] = useState('')
    const [trainDryRun, setTrainDryRun] = useState(true)

    const [btConfig, setBtConfig] = useState('configs/backtest/base.yaml')
    const [btTickers, setBtTickers] = useState('TSM')
    const [btStart, setBtStart] = useState('')
    const [btEnd, setBtEnd] = useState('')
    const [btOverrides, setBtOverrides] = useState('')
    const [btDryRun, setBtDryRun] = useState(true)

    const [notice, setNotice] = useState<JobRecord | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [submitting, setSubmitting] = useState(false)

    const onCreateTrain = async (e: FormEvent) => {
        e.preventDefault()
        setSubmitting(true)
        setError(null)
        try {
            const job = await api.jobs.createTrain({
                config_path: trainConfig,
                overrides: parseOverrides(trainOverrides),
                dry_run: trainDryRun,
            })
            setNotice(job)
        } catch (err: any) {
            setError(err.message || 'Create train job failed')
        } finally {
            setSubmitting(false)
        }
    }

    const onCreateBacktest = async (e: FormEvent) => {
        e.preventDefault()
        setSubmitting(true)
        setError(null)
        try {
            const job = await api.jobs.createBacktest({
                config_path: btConfig,
                tickers: parseTickers(btTickers),
                start: btStart || undefined,
                end: btEnd || undefined,
                overrides: parseOverrides(btOverrides),
                dry_run: btDryRun,
            })
            setNotice(job)
        } catch (err: any) {
            setError(err.message || 'Create backtest job failed')
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-gray-900">Actions</h1>
                <Link to="/jobs" className="text-sm text-indigo-700 hover:underline">
                    View Jobs
                </Link>
            </div>

            {notice && (
                <div className="rounded-md bg-green-50 border border-green-200 px-3 py-2 text-sm text-green-800">
                    Job created: <span className="font-mono">{notice.job_id}</span>{' '}
                    <Link className="underline" to={`/jobs/${notice.job_id}`}>
                        Open detail
                    </Link>
                </div>
            )}
            {error && <div className="rounded-md bg-red-50 text-red-700 px-3 py-2 text-sm">{error}</div>}

            <section className="bg-white border border-gray-200 rounded-lg p-4">
                <h2 className="text-lg font-semibold text-gray-900 mb-3">Run Training</h2>
                <form onSubmit={onCreateTrain} className="space-y-3">
                    <label className="block text-sm font-medium text-gray-700">
                        Config Path
                        <input
                            className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                            value={trainConfig}
                            onChange={(e) => setTrainConfig(e.target.value)}
                        />
                    </label>
                    <label className="block text-sm font-medium text-gray-700">
                        Overrides (one key=value per line)
                        <textarea
                            className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 min-h-24 font-mono text-sm"
                            value={trainOverrides}
                            onChange={(e) => setTrainOverrides(e.target.value)}
                            placeholder="label.horizon_days=40"
                        />
                    </label>
                    <label className="inline-flex items-center gap-2 text-sm text-gray-700">
                        <input type="checkbox" checked={trainDryRun} onChange={(e) => setTrainDryRun(e.target.checked)} />
                        Dry Run
                    </label>
                    <div>
                        <button
                            disabled={submitting}
                            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-60"
                        >
                            Trigger Train Job
                        </button>
                    </div>
                </form>
            </section>

            <section className="bg-white border border-gray-200 rounded-lg p-4">
                <h2 className="text-lg font-semibold text-gray-900 mb-3">Run Backtest</h2>
                <form onSubmit={onCreateBacktest} className="space-y-3">
                    <label className="block text-sm font-medium text-gray-700">
                        Config Path
                        <input
                            className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                            value={btConfig}
                            onChange={(e) => setBtConfig(e.target.value)}
                        />
                    </label>
                    <label className="block text-sm font-medium text-gray-700">
                        Tickers (comma separated)
                        <input
                            className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                            value={btTickers}
                            onChange={(e) => setBtTickers(e.target.value)}
                            placeholder="TSM,NVDA"
                        />
                    </label>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <label className="block text-sm font-medium text-gray-700">
                            Start (YYYY-MM-DD)
                            <input
                                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                                value={btStart}
                                onChange={(e) => setBtStart(e.target.value)}
                                placeholder="2025-01-01"
                            />
                        </label>
                        <label className="block text-sm font-medium text-gray-700">
                            End (YYYY-MM-DD)
                            <input
                                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                                value={btEnd}
                                onChange={(e) => setBtEnd(e.target.value)}
                                placeholder="2025-12-31"
                            />
                        </label>
                    </div>
                    <label className="block text-sm font-medium text-gray-700">
                        Overrides (one key=value per line)
                        <textarea
                            className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 min-h-24 font-mono text-sm"
                            value={btOverrides}
                            onChange={(e) => setBtOverrides(e.target.value)}
                            placeholder="strategy.exit.stop_loss_pct=0.1"
                        />
                    </label>
                    <label className="inline-flex items-center gap-2 text-sm text-gray-700">
                        <input type="checkbox" checked={btDryRun} onChange={(e) => setBtDryRun(e.target.checked)} />
                        Dry Run
                    </label>
                    <div>
                        <button
                            disabled={submitting}
                            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-60"
                        >
                            Trigger Backtest Job
                        </button>
                    </div>
                </form>
            </section>
        </div>
    )
}
