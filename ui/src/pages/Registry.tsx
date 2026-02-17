import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Search } from 'lucide-react'
import { api } from '@/api/client'
import { RegistryModelRow } from '@/types/api'

export default function Registry() {
    const [tickerFilter, setTickerFilter] = useState('')
    const [liftMin, setLiftMin] = useState('')
    const [precisionMin, setPrecisionMin] = useState('')
    const [models, setModels] = useState<RegistryModelRow[]>([])
    const [filteredModels, setFilteredModels] = useState<RegistryModelRow[]>([])
    const [loading, setLoading] = useState(false)
    const [offset, setOffset] = useState(0)
    const [notice, setNotice] = useState<string | null>(null)
    const LIMIT = 50

    async function fetchModels(reset = false) {
        setLoading(true)
        try {
            const currentOffset = reset ? 0 : offset
            const data = await api.registry.getModels({
                ticker: tickerFilter || undefined,
                limit: LIMIT,
                offset: currentOffset,
            })
            setModels(data)
            setFilteredModels(data)
            if (reset) setOffset(0)
        } catch (e) {
            console.error('Failed to fetch registry models', e)
        } finally {
            setLoading(false)
        }
    }

    const runBacktest = async (ticker: string, modelPath: string) => {
        try {
            const job = await api.jobs.createBacktest({
                config_path: 'configs/backtest/base.yaml',
                tickers: [ticker],
                model_path: modelPath,
                dry_run: false,
            })
            setNotice(`Backtest job created: ${job.job_id}`)
        } catch (e: any) {
            setNotice(`Create job failed: ${e.message}`)
        }
    }

    useEffect(() => {
        fetchModels(true)
    }, [])

    useEffect(() => {
        const filtered = models.filter((model) => {
            if (tickerFilter && !model.ticker.includes(tickerFilter.toUpperCase())) return false
            if (liftMin && model.lift < parseFloat(liftMin)) return false
            if (precisionMin && model.precision < parseFloat(precisionMin)) return false
            return true
        })
        setFilteredModels(filtered)
    }, [tickerFilter, liftMin, precisionMin, models])

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            fetchModels(true)
        }
    }

    const handleNext = () => {
        setOffset((prev) => prev + LIMIT)
        setTimeout(() => {
            api.registry
                .getModels({ ticker: tickerFilter || undefined, limit: LIMIT, offset: offset + LIMIT })
                .then(setModels)
        }, 0)
    }

    const handlePrev = () => {
        if (offset < LIMIT) return
        setOffset((prev) => prev - LIMIT)
        setTimeout(() => {
            api.registry
                .getModels({ ticker: tickerFilter || undefined, limit: LIMIT, offset: offset - LIMIT })
                .then(setModels)
        }, 0)
    }

    return (
        <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-6">Model Registry</h1>

            {notice && <div className="mb-4 rounded-md bg-indigo-50 text-indigo-800 px-3 py-2 text-sm">{notice}</div>}

            <div className="mb-6 flex gap-4">
                <div className="relative flex-1 max-w-sm">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <Search className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                        type="text"
                        className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                        placeholder="Filter by Ticker"
                        value={tickerFilter}
                        onChange={(e) => setTickerFilter(e.target.value)}
                        onKeyDown={handleKeyDown}
                    />
                </div>
                <input
                    type="number"
                    placeholder="Min Lift (e.g. 1.1)"
                    className="px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-indigo-500 w-40"
                    value={liftMin}
                    onChange={(e) => setLiftMin(e.target.value)}
                    step="0.1"
                />
                <input
                    type="number"
                    placeholder="Min Precision"
                    className="px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-indigo-500 w-40"
                    value={precisionMin}
                    onChange={(e) => setPrecisionMin(e.target.value)}
                    step="0.05"
                />
                <button
                    onClick={() => fetchModels(true)}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none"
                >
                    Refetch
                </button>
            </div>

            <div className="bg-white shadow overflow-hidden rounded-lg">
                {loading ? (
                    <div className="p-8 text-center text-gray-500">Loading models...</div>
                ) : models.length === 0 ? (
                    <div className="p-8 text-center text-gray-500">No models found</div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ticker</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Run ID</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Label (H/TH)</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Precision</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Lift</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Buy Rate</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Pos Rate</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">TP / FP</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {filteredModels.map((row, idx) => (
                                    <tr key={`${row.run_id}-${row.ticker}-${idx}`} className="hover:bg-gray-50">
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{row.ticker}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
                                            <Link to={`/runs/${row.run_id}`} className="text-indigo-600 hover:text-indigo-900">
                                                {row.run_id.substring(0, 8)}...
                                            </Link>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {row.label_horizon_days}d / {row.label_threshold ? (row.label_threshold * 100).toFixed(0) + '%' : '-'}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{(row.precision * 100).toFixed(1)}%</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{row.lift.toFixed(2)}x</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{(row.buy_rate * 100).toFixed(1)}%</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {row.positive_rate ? (row.positive_rate * 100).toFixed(1) + '%' : '-'}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {row.tp ?? '-'} / {row.fp ?? '-'}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-indigo-600 hover:text-indigo-900">
                                            <div className="flex space-x-3">
                                                <Link to={`/runs/${row.run_id}`} className="hover:underline">
                                                    Details
                                                </Link>
                                                <button className="hover:underline" onClick={() => runBacktest(row.ticker, row.model_path)}>
                                                    Run Backtest
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                <div className="bg-gray-50 px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
                    <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                        <div>
                            <p className="text-sm text-gray-700">
                                Showing <span className="font-medium">{offset + 1}</span> to{' '}
                                <span className="font-medium">{offset + models.length}</span> results
                            </p>
                        </div>
                        <div>
                            <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                                <button
                                    onClick={handlePrev}
                                    disabled={offset === 0}
                                    className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:bg-gray-100 disabled:cursor-not-allowed"
                                >
                                    <span className="sr-only">Previous</span>
                                    <ChevronLeft className="h-5 w-5" aria-hidden="true" />
                                </button>
                                <button
                                    onClick={handleNext}
                                    disabled={models.length < LIMIT}
                                    className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:bg-gray-100 disabled:cursor-not-allowed"
                                >
                                    <span className="sr-only">Next</span>
                                    <ChevronRight className="h-5 w-5" aria-hidden="true" />
                                </button>
                            </nav>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

