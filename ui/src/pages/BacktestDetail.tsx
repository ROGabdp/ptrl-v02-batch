import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '@/api/client'
import { BacktestDetail as IBacktestDetail } from '@/types/api'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Activity, FileText } from 'lucide-react'

export default function BacktestDetail() {
    const { btId } = useParams<{ btId: string }>()
    const [backtest, setBacktest] = useState<IBacktestDetail | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        if (!btId) return
        async function fetchDetail() {
            try {
                const data = await api.backtests.getDetail(btId!)
                setBacktest(data)
            } catch (e: any) {
                setError(e.message)
            } finally {
                setLoading(false)
            }
        }
        fetchDetail()
    }, [btId])

    if (loading) return <div className="p-8 text-center">Loading backtest...</div>
    if (error) return <div className="p-8 text-center text-red-600">Error: {error}</div>
    if (!backtest) return <div className="p-8 text-center text-gray-500">Backtest not found</div>

    const hasEquityData = backtest.equity_curve && backtest.equity_curve.length > 0
    const m = backtest.metrics

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">{backtest.ticker} Backtest</h1>
                    <p className="text-sm text-gray-500 font-mono">{backtest.bt_run_id}</p>
                </div>
                <div className="flex space-x-4">
                    <div className={`text-center px-4 py-2 rounded ${m.total_return >= 0 ? 'bg-green-100' : 'bg-red-100'}`}>
                        <div className="text-xs text-gray-500">Total Return</div>
                        <div className={`font-bold ${m.total_return >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                            {(m.total_return * 100).toFixed(1)}%
                        </div>
                    </div>
                    <div className="text-center px-4 py-2 bg-gray-100 rounded">
                        <div className="text-xs text-gray-500">CAGR</div>
                        <div className="font-bold text-gray-700">{(m.cagr * 100).toFixed(1)}%</div>
                    </div>
                    <div className="text-center px-4 py-2 bg-yellow-50 rounded">
                        <div className="text-xs text-gray-500">Max DD</div>
                        <div className="font-bold text-yellow-700">{(m.max_drawdown * 100).toFixed(1)}%</div>
                    </div>
                </div>
            </div>

            {/* Equity Curve */}
            <section className="bg-white shadow rounded-lg p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                    <Activity className="mr-2 h-5 w-5 text-gray-400" />
                    Equity Curve
                </h2>
                <div className="h-96 w-full">
                    {backtest.plot_path ? (
                        // If static plot exists, prefer it as it might verify backend plotting
                        <div className="w-full h-full flex justify-center items-center bg-gray-50 rounded">
                            <img src={backtest.plot_path} alt="Equity Curve" className="max-h-full max-w-full object-contain" />
                        </div>
                    ) : hasEquityData ? (
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={backtest.equity_curve}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis
                                    dataKey="date"
                                    tickFormatter={(str) => str.substring(0, 7)}
                                    minTickGap={30}
                                />
                                <YAxis domain={['auto', 'auto']} />
                                <Tooltip />
                                <Legend />
                                <Line
                                    type="monotone"
                                    dataKey="portfolio_value"
                                    stroke="#4f46e5"
                                    name="Strategy"
                                    dot={false}
                                    strokeWidth={2}
                                />
                                <Line
                                    type="monotone"
                                    dataKey="benchmark_value"
                                    stroke="#9ca3af"
                                    name="Benchmark"
                                    dot={false}
                                    strokeDasharray="5 5"
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    ) : (
                        <div className="w-full h-full flex items-center justify-center text-gray-400">
                            No Equity Data Available
                        </div>
                    )}
                </div>
            </section>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* End Date Summary */}
                <section className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                        <FileText className="mr-2 h-5 w-5 text-gray-400" />
                        End Date Summary
                    </h2>
                    <div className="bg-gray-50 rounded p-4 font-mono text-xs overflow-auto h-96 whitespace-pre-wrap">
                        {backtest.end_date_summary_text || backtest.summary_text || "No summary available."}
                    </div>
                </section>

                {/* Metrics Detail */}
                <section className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                        <Activity className="mr-2 h-5 w-5 text-gray-400" />
                        Detailed Metrics
                    </h2>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                        <div className="p-3 bg-gray-50 rounded">
                            <span className="block text-gray-500 text-xs">Win Rate</span>
                            <span className="font-semibold text-gray-900">{(m.win_rate * 100).toFixed(1)}%</span>
                        </div>
                        <div className="p-3 bg-gray-50 rounded">
                            <span className="block text-gray-500 text-xs">Trade Count</span>
                            <span className="font-semibold text-gray-900">{m.trade_count}</span>
                        </div>
                        <div className="p-3 bg-gray-50 rounded">
                            <span className="block text-gray-500 text-xs">Exposure Rate</span>
                            <span className="font-semibold text-gray-900">{(m.exposure_rate * 100).toFixed(1)}%</span>
                        </div>
                        <div className="p-3 bg-gray-50 rounded">
                            <span className="block text-gray-500 text-xs">Sharpe Ratio</span>
                            <span className="font-semibold text-gray-900">{m.sharpe_ratio?.toFixed(2) ?? 'N/A'}</span>
                        </div>
                        <div className="p-3 bg-gray-50 rounded">
                            <span className="block text-gray-500 text-xs">Sortino Ratio</span>
                            <span className="font-semibold text-gray-900">{m.sortino_ratio?.toFixed(2) ?? 'N/A'}</span>
                        </div>
                        <div className="p-3 bg-gray-50 rounded">
                            <span className="block text-gray-500 text-xs">Avg Trade Duration</span>
                            <span className="font-semibold text-gray-900">{m.avg_trade_duration?.toFixed(1)} days</span>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    )
}
