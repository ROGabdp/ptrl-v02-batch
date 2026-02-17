import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertCircle, ArrowRight, Calendar, TrendingUp } from 'lucide-react'
import { api } from '@/api/client'
import { BacktestSummary, JobRecord, RegistryBestModel, RunSummary } from '@/types/api'

export default function Dashboard() {
    const [bestModels, setBestModels] = useState<RegistryBestModel[]>([])
    const [recentRuns, setRecentRuns] = useState<RunSummary[]>([])
    const [recentBacktests, setRecentBacktests] = useState<BacktestSummary[]>([])
    const [recentJobs, setRecentJobs] = useState<JobRecord[]>([])
    const [loading, setLoading] = useState(true)
    const [notice, setNotice] = useState<string | null>(null)

    useEffect(() => {
        async function fetchData() {
            try {
                const [best, runs, bts, jobs] = await Promise.all([
                    api.registry.getBest().catch(() => []),
                    api.runs.getRecent(5).catch(() => []),
                    api.backtests.getRecent(5).catch(() => []),
                    api.jobs.getRecent(5).catch(() => []),
                ])
                setBestModels(best)
                setRecentRuns(runs)
                setRecentBacktests(bts)
                setRecentJobs(jobs)
            } catch (e) {
                console.error('Failed to fetch dashboard data', e)
            } finally {
                setLoading(false)
            }
        }

        fetchData()
    }, [])

    const onRunBacktest = async (ticker: string, modelPath: string) => {
        try {
            const job = await api.jobs.createBacktest({
                config_path: 'configs/backtest/base.yaml',
                tickers: [ticker],
                model_path: modelPath,
                dry_run: false,
            })
            setNotice(`Backtest job created: ${job.job_id}`)
            setRecentJobs((prev) => [job, ...prev].slice(0, 5))
        } catch (e: any) {
            setNotice(`Create job failed: ${e.message}`)
        }
    }

    if (loading) return <div className="p-4">Loading dashboard...</div>

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

                {notice && <div className="mb-4 rounded-md bg-indigo-50 text-indigo-800 px-3 py-2 text-sm">{notice}</div>}

                <section className="mb-8">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold text-gray-800">Best Models by Ticker</h2>
                        <Link to="/registry" className="text-sm text-indigo-600 hover:text-indigo-800 flex items-center">
                            View All <ArrowRight className="ml-1 h-4 w-4" />
                        </Link>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        {bestModels.slice(0, 4).map((model) => (
                            <div
                                key={model.ticker}
                                className="bg-white p-4 rounded-lg shadow-sm border border-gray-100 hover:shadow-md transition-shadow"
                            >
                                <div className="flex justify-between items-start mb-2">
                                    <span className="font-bold text-lg text-gray-900">{model.ticker}</span>
                                    <span className="text-xs font-mono bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                                        {model.run_id.substring(0, 8)}...
                                    </span>
                                </div>
                                <div className="grid grid-cols-2 gap-2">
                                    <div className="flex flex-col">
                                        <span className="text-gray-500 text-xs">Precision</span>
                                        <span className="font-medium text-green-600">{(model.precision * 100).toFixed(1)}%</span>
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-gray-500 text-xs">Lift</span>
                                        <span className="font-medium text-blue-600">{model.lift.toFixed(2)}x</span>
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-gray-500 text-xs">Label (H/TH)</span>
                                        <span className="font-medium text-gray-900">
                                            {model.label_horizon_days}d / {(model.label_threshold * 100).toFixed(0)}%
                                        </span>
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-gray-500 text-xs">Pos Rate</span>
                                        <span className="font-medium text-gray-900">
                                            {model.positive_rate ? (model.positive_rate * 100).toFixed(1) + '%' : '-'}
                                        </span>
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-gray-500 text-xs">TP / FP</span>
                                        <span className="font-medium text-gray-900">
                                            {model.tp ?? '-'} / {model.fp ?? '-'}
                                        </span>
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-gray-500 text-xs">Buy Rate</span>
                                        <span className="font-medium text-gray-700">{(model.buy_rate * 100).toFixed(1)}%</span>
                                    </div>
                                </div>
                                <div className="mt-4 flex space-x-2">
                                    <Link
                                        to={`/runs/${model.run_id}`}
                                        className="flex-1 text-center px-2 py-1 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50"
                                    >
                                        Run
                                    </Link>
                                    {(() => {
                                        const bt = recentBacktests.find((b) => b.ticker === model.ticker)
                                        return bt ? (
                                            <Link
                                                to={`/backtests/${bt.bt_run_id}`}
                                                className="flex-1 text-center px-2 py-1 border border-transparent shadow-sm text-xs font-medium rounded text-white bg-indigo-600 hover:bg-indigo-700"
                                            >
                                                Backtest
                                            </Link>
                                        ) : (
                                            <button
                                                disabled
                                                className="flex-1 text-center px-2 py-1 border border-gray-200 text-xs font-medium rounded text-gray-300 bg-gray-50 cursor-not-allowed"
                                            >
                                                No BT
                                            </button>
                                        )
                                    })()}
                                </div>
                                <button
                                    onClick={() => onRunBacktest(model.ticker, model.model_path)}
                                    className="mt-2 w-full text-center px-2 py-1 border border-indigo-200 text-xs font-medium rounded text-indigo-700 bg-indigo-50 hover:bg-indigo-100"
                                >
                                    Run Backtest with this model
                                </button>
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
                                        <span
                                            className={`text-xs px-2 py-1 rounded-full ${
                                                run.status === 'COMPLETED' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                                            }`}
                                        >
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
                            {recentRuns.length === 0 && <div className="p-6 text-center text-gray-500">No recent runs found</div>}
                        </div>
                    </section>

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
                                        <span
                                            className={`text-xs px-2 py-1 rounded font-medium ${
                                                bt.total_return >= 0 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                                            }`}
                                        >
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
                                    <div className="mt-2 text-xs text-gray-400 font-mono">{bt.bt_run_id.split('__')[0]}</div>
                                </Link>
                            ))}
                            {recentBacktests.length === 0 && <div className="p-6 text-center text-gray-500">No recent backtests found</div>}
                        </div>
                    </section>
                </div>

                <section className="mt-8">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold text-gray-800">Recent Jobs</h2>
                        <Link to="/jobs" className="text-sm text-indigo-600 hover:text-indigo-800 flex items-center">
                            View All <ArrowRight className="ml-1 h-4 w-4" />
                        </Link>
                    </div>
                    <div className="bg-white rounded-lg shadow-sm border border-gray-100 divide-y divide-gray-100">
                        {recentJobs.map((job) => (
                            <Link key={job.job_id} to={`/jobs/${job.job_id}`} className="block p-4 hover:bg-gray-50 transition-colors">
                                <div className="flex justify-between items-center mb-1">
                                    <span className="font-mono text-sm text-indigo-700">{job.job_id}</span>
                                    <span className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-800">{job.status}</span>
                                </div>
                                <div className="text-sm text-gray-600">
                                    {job.job_type} ¡P {job.command.slice(0, 5).join(' ')}
                                </div>
                            </Link>
                        ))}
                        {recentJobs.length === 0 && <div className="p-6 text-center text-gray-500">No recent jobs found</div>}
                    </div>
                </section>
            </div>
        </div>
    )
}

