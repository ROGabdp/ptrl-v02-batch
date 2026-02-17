import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '@/api/client'
import { RunDetail as IRunDetail } from '@/types/api'
import { FileText, Database, Layers, Copy, ChevronDown, ChevronUp } from 'lucide-react'

export default function RunDetail() {
    const { runId } = useParams<{ runId: string }>()
    const [run, setRun] = useState<IRunDetail | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [checkpoints, setCheckpoints] = useState<string[]>([])
    const [loadingCheckpoints, setLoadingCheckpoints] = useState(false)
    const [showCheckpoints, setShowCheckpoints] = useState({ base: false, finetuned: {} as Record<string, boolean> })

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text)
    }

    const toggleCheckpoints = async (mode: 'base' | 'finetuned', _ticker?: string) => {
        if (mode === 'base') {
            if (!showCheckpoints.base) {
                if (checkpoints.length === 0) {
                    setLoadingCheckpoints(true)
                    try {
                        const data = await api.runs.getCheckpoints(runId!, 'base')
                        setCheckpoints(data)
                    } catch (e) {
                        console.error('Failed to load checkpoints', e)
                    } finally {
                        setLoadingCheckpoints(false)
                    }
                }
            }
            setShowCheckpoints((prev) => ({ ...prev, base: !prev.base }))
        }
    }

    useEffect(() => {
        if (!runId) return
        async function fetchDetail() {
            try {
                const data = await api.runs.getDetail(runId!)
                setRun(data)
            } catch (e: any) {
                setError(e.message)
            } finally {
                setLoading(false)
            }
        }
        fetchDetail()
    }, [runId])

    if (loading) return <div className="p-8 text-center">Loading run details...</div>
    if (error) return <div className="p-8 text-center text-red-600">Error: {error}</div>
    if (!run || !runId) return <div className="p-8 text-center text-gray-500">Run not found</div>

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h1 className="text-2xl font-bold text-gray-900 font-mono">Run: {run.run_id}</h1>
                <div className="flex items-center gap-3">
                    <Link
                        to={`/actions?type=eval&run_id=${encodeURIComponent(runId)}`}
                        className="px-3 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700"
                    >
                        Open Eval in Actions
                    </Link>
                    <span className="text-sm text-gray-500">
                        {run.manifest.start_time ? new Date(run.manifest.start_time).toLocaleString() : ''}
                    </span>
                </div>
            </div>

            {run.metrics && Object.keys(run.metrics).length > 0 && (
                <section className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                        <Layers className="mr-2 h-5 w-5 text-gray-400" />
                        Validation Metrics
                    </h2>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="col-span-4 bg-gray-50 p-4 rounded text-xs font-mono overflow-auto max-h-64">
                            <pre>{JSON.stringify(run.metrics, null, 2)}</pre>
                        </div>
                    </div>
                </section>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <section className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                        <FileText className="mr-2 h-5 w-5 text-gray-400" />
                        Configuration
                    </h2>
                    <div className="space-y-3 text-sm">
                        <div>
                            <span className="font-semibold text-gray-700">Universe: </span>
                            <span className="text-gray-600">{run.config.universe?.tickers?.join(', ') || 'N/A'}</span>
                        </div>
                        <div>
                            <span className="font-semibold text-gray-700">Label: </span>
                            <span className="text-gray-600">
                                Horizon={run.config.label?.horizon_days || '?'}, Thresh={run.config.label?.threshold || '?'}
                            </span>
                        </div>
                        <div>
                            <span className="font-semibold text-gray-700">Train: </span>
                            <span className="text-gray-600">
                                Steps={run.config.train?.total_timesteps}, Ent={run.config.train?.ppo_params?.ent_coef}
                            </span>
                        </div>
                    </div>
                    <div className="mt-4">
                        <details className="text-xs text-gray-500 cursor-pointer">
                            <summary>Full Config JSON</summary>
                            <pre className="mt-2 bg-gray-50 p-2 rounded overflow-auto max-h-48">{JSON.stringify(run.config, null, 2)}</pre>
                        </details>
                    </div>
                </section>

                <section className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                        <Database className="mr-2 h-5 w-5 text-gray-400" />
                        Generated Models
                    </h2>
                    <div className="space-y-4">
                        <div>
                            <h3 className="text-sm font-semibold text-gray-700 mb-2">Base Models</h3>
                            <div className="bg-gray-50 rounded p-2 text-xs font-mono space-y-2">
                                {run.models.base.length > 0 ? (
                                    <ul className="list-disc pl-4 space-y-1">
                                        {run.models.base.map((m) => (
                                            <li key={m} className="flex items-center justify-between group">
                                                <span>{m}</span>
                                                <button
                                                    onClick={() => copyToClipboard(m)}
                                                    className="text-gray-400 hover:text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity"
                                                >
                                                    <Copy className="h-3 w-3" />
                                                </button>
                                            </li>
                                        ))}
                                    </ul>
                                ) : (
                                    <span className="text-gray-400">No key models found</span>
                                )}

                                {run.checkpoints_count > 0 && (
                                    <div className="border-t border-gray-200 pt-2 mt-2">
                                        <button
                                            onClick={() => toggleCheckpoints('base')}
                                            className="flex items-center text-indigo-600 hover:text-indigo-800 text-xs font-medium focus:outline-none"
                                        >
                                            {showCheckpoints.base ? (
                                                <ChevronUp className="h-3 w-3 mr-1" />
                                            ) : (
                                                <ChevronDown className="h-3 w-3 mr-1" />
                                            )}
                                            {showCheckpoints.base ? 'Hide' : `Show All ${run.checkpoints_count} Checkpoints`}
                                        </button>

                                        {showCheckpoints.base && (
                                            <div className="mt-2 pl-4 max-h-48 overflow-y-auto">
                                                {loadingCheckpoints ? (
                                                    <div className="text-gray-400 italic">Loading...</div>
                                                ) : (
                                                    <ul className="list-disc space-y-1 text-gray-600">
                                                        {checkpoints.map((cp) => (
                                                            <li key={cp} className="flex items-center justify-between group">
                                                                <span>{cp}</span>
                                                                <button
                                                                    onClick={() => copyToClipboard(cp)}
                                                                    className="text-gray-400 hover:text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity"
                                                                >
                                                                    <Copy className="h-3 w-3" />
                                                                </button>
                                                            </li>
                                                        ))}
                                                    </ul>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                        <div>
                            <h3 className="text-sm font-semibold text-gray-700 mb-2">Finetuned Models</h3>
                            <div className="bg-gray-50 rounded p-2 text-xs font-mono max-h-48 overflow-y-auto">
                                {Object.keys(run.models.finetuned).length > 0 ? (
                                    <ul className="space-y-2">
                                        {Object.entries(run.models.finetuned).map(([ticker, models]) => (
                                            <li key={ticker}>
                                                <span className="font-bold">{ticker}:</span> {models.join(', ')}
                                            </li>
                                        ))}
                                    </ul>
                                ) : (
                                    <span className="text-gray-400">No finetuned models</span>
                                )}
                            </div>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    )
}