import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '@/api/client'
import { JobRecord } from '@/types/api'

type ActionTab = 'train' | 'backtest' | 'eval'

function parseOverrides(raw: string): string[] {
    return raw
        .split('\n')
        .map((x) => x.trim())
        .filter((x) => x && !x.startsWith('#'))
}

function parseTickers(raw: string): string[] {
    return raw
        .split(',')
        .map((x) => x.trim().toUpperCase())
        .filter(Boolean)
}

function parseOverridesObject(raw: string): { parsed: Record<string, string>; errors: string[] } {
    const parsed: Record<string, string> = {}
    const errors: string[] = []
    const lines = raw.split('\n')
    lines.forEach((line, idx) => {
        const s = line.trim()
        if (!s || s.startsWith('#')) return
        const eq = s.indexOf('=')
        if (eq <= 0) {
            errors.push(`Line ${idx + 1}: missing '='`) 
            return
        }
        const key = s.slice(0, eq).trim()
        const val = s.slice(eq + 1).trim()
        if (!key) {
            errors.push(`Line ${idx + 1}: empty key`) 
            return
        }
        parsed[key] = val
    })
    return { parsed, errors }
}

export default function Actions() {
    const [searchParams] = useSearchParams()

    const [activeTab, setActiveTab] = useState<ActionTab>('train')

    const [trainConfig, setTrainConfig] = useState('configs/base.yaml')
    const [trainOverrides, setTrainOverrides] = useState('')
    const [trainDryRun, setTrainDryRun] = useState(true)

    const [btConfig, setBtConfig] = useState('configs/backtest/base.yaml')
    const [btTickers, setBtTickers] = useState('TSM')
    const [btModelPath, setBtModelPath] = useState('')
    const [btStart, setBtStart] = useState('')
    const [btEnd, setBtEnd] = useState('')
    const [btOverrides, setBtOverrides] = useState('')
    const [btDryRun, setBtDryRun] = useState(true)

    const [evalRunId, setEvalRunId] = useState('')
    const [evalMode, setEvalMode] = useState<'base' | 'finetune'>('finetune')
    const [evalDryRun, setEvalDryRun] = useState(true)

    const [notice, setNotice] = useState<JobRecord | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [submitting, setSubmitting] = useState(false)

    useEffect(() => {
        const type = searchParams.get('type') as ActionTab | null
        if (type && ['train', 'backtest', 'eval'].includes(type)) {
            setActiveTab(type)
        }

        const configPath = searchParams.get('config_path')
        if (configPath) {
            if ((type || activeTab) === 'train') setTrainConfig(configPath)
            else setBtConfig(configPath)
        }

        const ticker = searchParams.get('ticker')
        if (ticker) setBtTickers(ticker.toUpperCase())

        const modelPath = searchParams.get('model_path')
        if (modelPath) setBtModelPath(modelPath)

        const start = searchParams.get('start')
        if (start) setBtStart(start)

        const end = searchParams.get('end')
        if (end) setBtEnd(end)

        const runId = searchParams.get('run_id')
        if (runId) setEvalRunId(runId)
    }, [searchParams])

    const trainPreview = useMemo(() => parseOverridesObject(trainOverrides), [trainOverrides])
    const btPreview = useMemo(() => parseOverridesObject(btOverrides), [btOverrides])

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
            const tickers = parseTickers(btTickers)
            const payload: any = {
                config_path: btConfig,
                tickers,
                start: btStart || undefined,
                end: btEnd || undefined,
                overrides: parseOverrides(btOverrides),
                dry_run: btDryRun,
            }
            if (btModelPath) payload.model_path = btModelPath
            const job = await api.jobs.createBacktest(payload)
            setNotice(job)
        } catch (err: any) {
            setError(err.message || 'Create backtest job failed')
        } finally {
            setSubmitting(false)
        }
    }

    const onCreateEval = async (e: FormEvent) => {
        e.preventDefault()
        setSubmitting(true)
        setError(null)
        try {
            const job = await api.jobs.createEvalMetrics({
                run_id: evalRunId,
                mode: evalMode,
                dry_run: evalDryRun,
            })
            setNotice(job)
        } catch (err: any) {
            setError(err.message || 'Create eval-metrics job failed')
        } finally {
            setSubmitting(false)
        }
    }

    const copyJson = async (obj: object) => {
        await navigator.clipboard.writeText(JSON.stringify(obj, null, 2))
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-gray-900">Actions</h1>
                <Link to="/jobs" className="text-sm text-indigo-700 hover:underline">
                    View Jobs
                </Link>
            </div>

            <div className="flex gap-2">
                {(['train', 'backtest', 'eval'] as ActionTab[]).map((tab) => (
                    <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`px-3 py-1.5 rounded border text-sm ${activeTab === tab ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-700 border-gray-300'}`}
                    >
                        {tab}
                    </button>
                ))}
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

            {activeTab === 'train' && (
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
                        {trainPreview.errors.length > 0 && (
                            <div className="text-xs text-red-600">{trainPreview.errors.join(' | ')}</div>
                        )}
                        <div className="rounded border border-gray-200 bg-gray-50 p-2">
                            <div className="text-xs text-gray-600 mb-1">Parsed Overrides Preview</div>
                            <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(trainPreview.parsed, null, 2)}</pre>
                            <button type="button" onClick={() => copyJson(trainPreview.parsed)} className="mt-2 text-xs text-indigo-700 hover:underline">Copy JSON</button>
                        </div>
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
            )}

            {activeTab === 'backtest' && (
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
                        <label className="block text-sm font-medium text-gray-700">
                            Model Path (optional, single ticker only)
                            <input
                                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                                value={btModelPath}
                                onChange={(e) => setBtModelPath(e.target.value)}
                                placeholder="runs/<run_id>/models/finetuned/TSM/final.zip"
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
                        {btPreview.errors.length > 0 && (
                            <div className="text-xs text-red-600">{btPreview.errors.join(' | ')}</div>
                        )}
                        <div className="rounded border border-gray-200 bg-gray-50 p-2">
                            <div className="text-xs text-gray-600 mb-1">Parsed Overrides Preview</div>
                            <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(btPreview.parsed, null, 2)}</pre>
                            <button type="button" onClick={() => copyJson(btPreview.parsed)} className="mt-2 text-xs text-indigo-700 hover:underline">Copy JSON</button>
                        </div>
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
            )}

            {activeTab === 'eval' && (
                <section className="bg-white border border-gray-200 rounded-lg p-4">
                    <h2 className="text-lg font-semibold text-gray-900 mb-3">Recompute Metrics</h2>
                    <form onSubmit={onCreateEval} className="space-y-3">
                        <label className="block text-sm font-medium text-gray-700">
                            Run ID
                            <input
                                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 font-mono"
                                value={evalRunId}
                                onChange={(e) => setEvalRunId(e.target.value)}
                                placeholder="20260217_101010__abcd1234"
                            />
                        </label>
                        <label className="block text-sm font-medium text-gray-700">
                            Mode
                            <select className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2" value={evalMode} onChange={(e) => setEvalMode(e.target.value as 'base' | 'finetune')}>
                                <option value="finetune">finetune</option>
                                <option value="base">base</option>
                            </select>
                        </label>
                        <label className="inline-flex items-center gap-2 text-sm text-gray-700">
                            <input type="checkbox" checked={evalDryRun} onChange={(e) => setEvalDryRun(e.target.checked)} />
                            Dry Run
                        </label>
                        <div>
                            <button
                                disabled={submitting || !evalRunId}
                                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-60"
                            >
                                Trigger Eval-Metrics Job
                            </button>
                        </div>
                    </form>
                </section>
            )}
        </div>
    )
}