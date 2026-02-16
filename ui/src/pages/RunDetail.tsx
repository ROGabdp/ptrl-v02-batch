import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '@/api/client'
import { RunDetail as IRunDetail } from '@/types/api'
import { FileText, Database, Layers } from 'lucide-react'

export default function RunDetail() {
    const { runId } = useParams<{ runId: string }>()
    const [run, setRun] = useState<IRunDetail | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

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
    if (!run) return <div className="p-8 text-center text-gray-500">Run not found</div>

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h1 className="text-2xl font-bold text-gray-900 font-mono">Run: {run.run_id}</h1>
                <span className="text-sm text-gray-500">
                    {run.manifest.start_time ? new Date(run.manifest.start_time).toLocaleString() : ''}
                </span>
            </div>

            {/* Metrics Summary */}
            {run.metrics && Object.keys(run.metrics).length > 0 && (
                <section className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                        <Layers className="mr-2 h-5 w-5 text-gray-400" />
                        Validation Metrics
                    </h2>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {/* Flatten relevant metrics or show raw JSON */}
                        <div className="col-span-4 bg-gray-50 p-4 rounded text-xs font-mono overflow-auto max-h-64">
                            <pre>{JSON.stringify(run.metrics, null, 2)}</pre>
                        </div>
                    </div>
                </section>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Config Summary */}
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
                                Horizon={run.config.label?.horizon_days || '?'},
                                Thresh={run.config.label?.threshold || '?'}
                            </span>
                        </div>
                        <div>
                            <span className="font-semibold text-gray-700">Train: </span>
                            <span className="text-gray-600">
                                Steps={run.config.train?.total_timesteps},
                                Ent={run.config.train?.ppo_params?.ent_coef}
                            </span>
                        </div>
                    </div>
                    <div className="mt-4">
                        <details className="text-xs text-gray-500 cursor-pointer">
                            <summary>Full Config JSON</summary>
                            <pre className="mt-2 bg-gray-50 p-2 rounded overflow-auto max-h-48">
                                {JSON.stringify(run.config, null, 2)}
                            </pre>
                        </details>
                    </div>
                </section>

                {/* Models */}
                <section className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                        <Database className="mr-2 h-5 w-5 text-gray-400" />
                        Generated Models
                    </h2>
                    <div className="space-y-4">
                        <div>
                            <h3 className="text-sm font-semibold text-gray-700 mb-2">Base Models</h3>
                            <div className="bg-gray-50 rounded p-2 text-xs font-mono">
                                {run.models.base.length > 0 ? (
                                    <ul className="list-disc pl-4 space-y-1">
                                        {run.models.base.map(m => <li key={m}>{m}</li>)}
                                    </ul>
                                ) : <span className="text-gray-400">No base models</span>}
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
                                ) : <span className="text-gray-400">No finetuned models</span>}
                            </div>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    )
}
