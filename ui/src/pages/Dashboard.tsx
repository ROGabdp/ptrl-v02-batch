import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import { RegistryBestModel, RunSummary, BacktestSummary } from '@/types/api'
import { Link } from 'react-router-dom'
import { ArrowRight, TrendingUp, Calendar, AlertCircle } from 'lucide-react'

export default function Dashboard() {
    const [bestModels, setBestModels] = useState<RegistryBestModel[]>([])
    const [recentRuns, setRecentRuns] = useState<RunSummary[]>([])
    const [recentBacktests, setRecentBacktests] = useState<BacktestSummary[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        async function fetchData() {
            try {
                const [best, runs, bts] = await Promise.all([
                    api.registry.getBest().catch(() => []),
                    api.runs.getRecent(5).catch(() => []),
                    api.backtests.getRecent(5).catch(() => [])
                ])
                setBestModels(best)
                setRecentRuns(runs)
                setRecentBacktests(bts)
            } catch (e) {
                console.error('Failed to fetch dashboard data', e)
            } finally {
                setLoading(false)
            }
        }
        fetchData()
    }, [])

    if (loading) return <div className="p-4">Loading dashboard...</div>

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

                {/* Best Models Section */}
                <section className="mb-8">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold text-gray-800">Best Models by Ticker</h2>
                        <Link to="/registry" className="text-sm text-indigo-600 hover:text-indigo-800 flex items-center">
                            View All <ArrowRight className="ml-1 h-4 w-4" />
                        </Link>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        {bestModels.slice(0, 4).map((model) => (
                            <div key={model.ticker} className="bg-white p-4 rounded-lg shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                                <div className="flex justify-between items-start mb-2">
                                    <span className="font-bold text-lg text-gray-900">{model.ticker}</span>
                                    <span className="text-xs font-mono bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                                        {model.run_id.substring(0, 8)}...
                                    </span>
                                </div>
                                <div className="space-y-1 text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-gray-500">Precision</span>
                                        <span className="font-medium text-green-600">{(model.precision * 100).toFixed(1)}%</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-500">Lift</span>
                                        <span className="font-medium text-blue-600">{model.lift.toFixed(2)}x</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-500">Buy Rate</span>
                                        <span className="font-medium text-gray-700">{(model.buy_rate * 100).toFixed(1)}%</span>
                                    </div>
                                </div>
                            </div>
                        ))}
                        {bestModels.length === 0 && (
                            <div className="col-span-4 p-8 text-center bg-gray-50 rounded-lg text-gray-500">
                                No best models found. Run registry index script first.
                            </div>
                        )}
                    </div>
                </section>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Recent Runs */}
                    <section>
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-lg font-semibold text-gray-800">Recent Training Runs</h2>
                            <Link to="/runs" className="text-sm text-indigo-600 hover:text-indigo-800 flex items-center">
                                View All <ArrowRight className="ml-1 h-4 w-4" />
                            </Link>
                        </div>
                        <div className="bg-white rounded-lg shadow-sm border border-gray-100 divide-y divide-gray-100">
                            {recentRuns.map((run) => (
                                <Link key={run.run_id} to={`/runs/${run.run_id}`} className="block p-4 hover:bg-gray-50 transition-colors">
                                    <div className="flex justify-between items-center mb-1">
                                        <span className="font-mono text-sm font-medium text-indigo-600">{run.run_id}</span>
                                        <span className={`text-xs px-2 py-1 rounded-full ${run.status === 'COMPLETED' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                                            }`}>
                                            {run.status}
                                        </span>
                                    </div>
                                    <div className="flex items-center text-sm text-gray-500 space-x-4">
                                        <span className="flex items-center">
                                            <Calendar className="mr-1 h-3 w-3" />
                                            {run.start_time ? new Date(run.start_time).toLocaleDateString() : 'Unknown'}
                                        </span>
                                        <span>{run.tickers.length > 0 ? `${run.tickers.length} tickers` : 'No tickers'}</span>
                                    </div>
                                </Link>
                            ))}
                            {recentRuns.length === 0 && (
                                <div className="p-6 text-center text-gray-500">No recent runs found</div>
                            )}
                        </div>
                    </section>

                    {/* Recent Backtests */}
                    <section>
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-lg font-semibold text-gray-800">Recent Backtests</h2>
                            <Link to="/backtests" className="text-sm text-indigo-600 hover:text-indigo-800 flex items-center">
                                View All <ArrowRight className="ml-1 h-4 w-4" />
                            </Link>
                        </div>
                        <div className="bg-white rounded-lg shadow-sm border border-gray-100 divide-y divide-gray-100">
                            {recentBacktests.map((bt) => (
                                <Link key={bt.bt_run_id} to={`/backtests/${bt.bt_run_id}`} className="block p-4 hover:bg-gray-50 transition-colors">
                                    <div className="flex justify-between items-center mb-1">
                                        <span className="font-bold text-gray-900">{bt.ticker}</span>
                                        <span className={`text-xs px-2 py-1 rounded font-medium ${bt.total_return >= 0 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                                            }`}>
                                            {(bt.total_return * 100).toFixed(1)}% Return
                                        </span>
                                    </div>
                                    <div className="grid grid-cols-2 gap-2 text-sm text-gray-500 mt-2">
                                        <div className="flex items-center">
                                            <TrendingUp className="mr-1 h-3 w-3" />
                                            CAGR: {(bt.cagr * 100).toFixed(1)}%
                                        </div>
                                        <div className="flex items-center">
                                            <AlertCircle className="mr-1 h-3 w-3" />
                                            MDD: {(bt.max_drawdown * 100).toFixed(1)}%
                                        </div>
                                    </div>
                                    <div className="mt-2 text-xs text-gray-400 font-mono">
                                        {bt.bt_run_id.split('__')[0]}
                                    </div>
                                </Link>
                            ))}
                            {recentBacktests.length === 0 && (
                                <div className="p-6 text-center text-gray-500">No recent backtests found</div>
                            )}
                        </div>
                    </section>
                </div>
            </div>
        </div>
    )
}
