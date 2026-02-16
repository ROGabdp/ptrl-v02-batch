import { useState, useEffect } from 'react'
import { api } from '@/api/client'
import { BacktestSummary } from '@/types/api'
import { Link } from 'react-router-dom'
import { Calendar, TrendingUp, AlertTriangle } from 'lucide-react'

export default function Backtests() {
    const [backtests, setBacktests] = useState<BacktestSummary[]>([])
    const [loading, setLoading] = useState(true)
    const LIMIT = 50

    useEffect(() => {
        async function fetchBacktests() {
            try {
                const data = await api.backtests.getRecent(LIMIT)
                setBacktests(data)
            } catch (e) {
                console.error('Failed to fetch backtests', e)
            } finally {
                setLoading(false)
            }
        }
        fetchBacktests()
    }, [])

    if (loading) return <div className="p-8 text-center text-gray-500">Loading backtests...</div>

    return (
        <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-6">Backtest Results</h1>

            <div className="bg-white shadow overflow-hidden rounded-md">
                <div className="grid grid-cols-1 divide-y divide-gray-200">
                    {backtests.map((bt) => (
                        <Link key={bt.bt_run_id} to={`/backtests/${bt.bt_run_id}`} className="block hover:bg-gray-50 transition-colors p-4 sm:px-6">
                            <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center">
                                    <span className="text-lg font-bold text-indigo-700 mr-3">{bt.ticker}</span>
                                    <span className="text-xs text-gray-500 font-mono bg-gray-100 px-2 py-0.5 rounded">
                                        {bt.bt_run_id.split('__')[0]}
                                    </span>
                                </div>
                                <span className={`text-sm font-semibold px-2.5 py-0.5 rounded-full ${bt.total_return >= 0 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                                    }`}>
                                    {(bt.total_return * 100).toFixed(1)}% Return
                                </span>
                            </div>

                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm text-gray-600">
                                <div className="flex items-center">
                                    <TrendingUp className="mr-1.5 h-4 w-4 text-gray-400" />
                                    CAGR: <span className="font-medium ml-1">{(bt.cagr * 100).toFixed(1)}%</span>
                                </div>
                                <div className="flex items-center">
                                    <AlertTriangle className="mr-1.5 h-4 w-4 text-gray-400" />
                                    MDD: <span className="font-medium ml-1">{(bt.max_drawdown * 100).toFixed(1)}%</span>
                                </div>
                                <div className="flex items-center">
                                    Win Rate: <span className="font-medium ml-1">{(bt.win_rate * 100).toFixed(1)}%</span>
                                </div>
                                <div className="flex items-center">
                                    Trades: <span className="font-medium ml-1">{bt.trade_count}</span>
                                </div>
                            </div>

                            <div className="mt-2 text-xs text-gray-400 flex justify-between">
                                <span>Model: {bt.model_path.split('/').pop()}</span>
                                <span className="flex items-center">
                                    <Calendar className="mr-1 h-3 w-3" />
                                    {bt.start_date} ~ {bt.end_date}
                                </span>
                            </div>
                        </Link>
                    ))}
                    {backtests.length === 0 && (
                        <div className="p-8 text-center text-gray-500">No recent backtests found.</div>
                    )}
                </div>
            </div>
        </div>
    )
}
