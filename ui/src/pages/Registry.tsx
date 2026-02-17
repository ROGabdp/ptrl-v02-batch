import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Search } from 'lucide-react'
import { api } from '@/api/client'
import { RegistryModelRow } from '@/types/api'
import CompareDrawer from '@/components/CompareDrawer'

const SORT_OPTIONS = [
    {
        label: 'Precision > Lift > BuyRate > Support',
        value: 'precision_desc,lift_desc,buy_rate_asc,support_desc',
    },
    {
        label: 'Lift > Precision > BuyRate > Support',
        value: 'lift_desc,precision_desc,buy_rate_asc,support_desc',
    },
    {
        label: 'Precision > Support > Lift > BuyRate',
        value: 'precision_desc,support_desc,lift_desc,buy_rate_asc',
    },
]

function pct(v?: number): string {
    if (v === undefined || v === null) return '-'
    return `${(v * 100).toFixed(1)}%`
}

export default function Registry() {
    const [tickerFilter, setTickerFilter] = useState('')
    const [liftMin, setLiftMin] = useState('')
    const [precisionMin, setPrecisionMin] = useState('')
    const [supportMin, setSupportMin] = useState('30')
    const [maxBuyRate, setMaxBuyRate] = useState('')
    const [sort, setSort] = useState(SORT_OPTIONS[0].value)
    const [models, setModels] = useState<RegistryModelRow[]>([])
    const [loading, setLoading] = useState(false)
    const [offset, setOffset] = useState(0)
    const [total, setTotal] = useState(0)
    const [error, setError] = useState<string | null>(null)
    const [selected, setSelected] = useState<Record<string, RegistryModelRow>>({})
    const [compareOpen, setCompareOpen] = useState(false)
    const [compareNotice, setCompareNotice] = useState<string | null>(null)
    const LIMIT = 50

    const compareItems = useMemo(() => Object.values(selected), [selected])

    const getCompareKey = (row: RegistryModelRow) => {
        const horizon = row.label_horizon_days ?? 'na'
        const threshold = row.label_threshold ?? 'na'
        const mode = row.mode ?? 'na'
        return `${row.ticker}::${row.run_id}::${mode}::${horizon}::${threshold}`
    }

    async function fetchModels(nextOffset = 0) {
        setLoading(true)
        setError(null)
        try {
            const res = await api.registry.getModels({
                ticker: tickerFilter || undefined,
                min_lift: liftMin ? parseFloat(liftMin) : undefined,
                min_precision: precisionMin ? parseFloat(precisionMin) : undefined,
                min_support: supportMin ? parseInt(supportMin, 10) : undefined,
                max_buy_rate: maxBuyRate ? parseFloat(maxBuyRate) : undefined,
                sort,
                limit: LIMIT,
                offset: nextOffset,
            })
            setModels(res.items)
            setTotal(res.total)
            setOffset(res.offset)
        } catch (e: any) {
            setError(e.message || 'Failed to fetch registry models')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchModels(0)
    }, [])

    const onRefetch = () => fetchModels(0)

    const handleNext = () => {
        const next = offset + LIMIT
        if (next >= total) return
        fetchModels(next)
    }

    const handlePrev = () => {
        const prev = Math.max(0, offset - LIMIT)
        fetchModels(prev)
    }

    const toggleSelect = (row: RegistryModelRow) => {
        const key = getCompareKey(row)
        setSelected((prev) => {
            const next = { ...prev }
            if (next[key]) {
                delete next[key]
                setCompareNotice(null)
                return next
            }
            if (Object.keys(next).length >= 4) {
                setCompareNotice('Compare \u6700\u591a\u53ef\u540c\u6642\u9078\u53d6 4 \u7b46')
                return next
            }
            next[key] = row
            setCompareNotice(null)
            return next
        })
    }

    return (
        <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-6">Model Registry</h1>

            <div className="mb-6 grid grid-cols-1 md:grid-cols-6 gap-3">
                <div className="relative md:col-span-2">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <Search className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                        type="text"
                        className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                        placeholder="Ticker"
                        value={tickerFilter}
                        onChange={(e) => setTickerFilter(e.target.value)}
                    />
                </div>
                <input
                    type="number"
                    placeholder="Min Lift"
                    className="px-3 py-2 border border-gray-300 rounded-md"
                    value={liftMin}
                    onChange={(e) => setLiftMin(e.target.value)}
                    step="0.1"
                />
                <input
                    type="number"
                    placeholder="Min Precision"
                    className="px-3 py-2 border border-gray-300 rounded-md"
                    value={precisionMin}
                    onChange={(e) => setPrecisionMin(e.target.value)}
                    step="0.05"
                />
                <input
                    type="number"
                    placeholder="Min Support"
                    className="px-3 py-2 border border-gray-300 rounded-md"
                    value={supportMin}
                    onChange={(e) => setSupportMin(e.target.value)}
                />
                <input
                    type="number"
                    placeholder="Max Buy Rate"
                    className="px-3 py-2 border border-gray-300 rounded-md"
                    value={maxBuyRate}
                    onChange={(e) => setMaxBuyRate(e.target.value)}
                    step="0.01"
                />
                <select
                    className="px-3 py-2 border border-gray-300 rounded-md md:col-span-2"
                    value={sort}
                    onChange={(e) => setSort(e.target.value)}
                >
                    {SORT_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                </select>
                <button
                    onClick={onRefetch}
                    className="px-4 py-2 text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
                >
                    Refetch
                </button>
                <button
                    disabled={compareItems.length < 2}
                    onClick={() => setCompareOpen(true)}
                    className="px-4 py-2 text-sm font-medium rounded-md border border-indigo-300 text-indigo-700 bg-indigo-50 disabled:opacity-50"
                >
                    Compare ({compareItems.length})
                </button>
            </div>

            {compareNotice && (
                <div className="mb-4 rounded-md bg-amber-50 text-amber-800 px-3 py-2 text-sm border border-amber-200">
                    {compareNotice}
                </div>
            )}
            {error && <div className="mb-4 rounded-md bg-red-50 text-red-700 px-3 py-2 text-sm">{error}</div>}

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
                                    <th className="px-4 py-3"></th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ticker</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Run ID</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Label (H/TH)</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Precision</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Lift</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Buy Rate</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Pos Rate</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Support</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">TP / FP</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {models.map((row, idx) => {
                                    const key = getCompareKey(row)
                                    const selectedRow = !!selected[key]
                                    const modelPath = row.model_final_path || ''
                                    const actionsHref = `/actions?type=backtest&ticker=${encodeURIComponent(row.ticker)}&model_path=${encodeURIComponent(modelPath)}`
                                    return (
                                        <tr key={`${row.run_id}-${row.ticker}-${idx}`} className="hover:bg-gray-50">
                                            <td className="px-4 py-4">
                                                <input
                                                    type="checkbox"
                                                    checked={selectedRow}
                                                    onChange={() => toggleSelect(row)}
                                                />
                                            </td>
                                            <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{row.ticker}</td>
                                            <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
                                                <Link to={`/runs/${row.run_id}`} className="text-indigo-600 hover:text-indigo-900">
                                                    {row.run_id.substring(0, 12)}...
                                                </Link>
                                            </td>
                                            <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {row.label_horizon_days ?? '-'}d / {pct(row.label_threshold)}
                                            </td>
                                            <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">{pct(row.precision)}</td>
                                            <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">{row.lift?.toFixed(2) ?? '-'}</td>
                                            <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">{pct(row.buy_rate)}</td>
                                            <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">{pct(row.positive_rate)}</td>
                                            <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">{row.support ?? '-'}</td>
                                            <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500" title={`TN=${row.tn ?? '-'} FN=${row.fn ?? '-'}`}>
                                                {row.tp ?? '-'} / {row.fp ?? '-'}
                                            </td>
                                            <td className="px-4 py-4 whitespace-nowrap text-sm text-indigo-600 hover:text-indigo-900">
                                                <div className="flex space-x-3">
                                                    <Link to={`/runs/${row.run_id}`} className="hover:underline">
                                                        Details
                                                    </Link>
                                                    <Link to={actionsHref} className="hover:underline">
                                                        Run Backtest
                                                    </Link>
                                                </div>
                                            </td>
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    </div>
                )}

                <div className="bg-gray-50 px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
                    <p className="text-sm text-gray-700">
                        Showing <span className="font-medium">{Math.min(offset + 1, total || 0)}</span> to{' '}
                        <span className="font-medium">{Math.min(offset + models.length, total)}</span> of{' '}
                        <span className="font-medium">{total}</span>
                    </p>
                    <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                        <button
                            onClick={handlePrev}
                            disabled={offset === 0}
                            className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm text-gray-500 hover:bg-gray-50 disabled:bg-gray-100 disabled:cursor-not-allowed"
                        >
                            <ChevronLeft className="h-5 w-5" aria-hidden="true" />
                        </button>
                        <button
                            onClick={handleNext}
                            disabled={offset + LIMIT >= total}
                            className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm text-gray-500 hover:bg-gray-50 disabled:bg-gray-100 disabled:cursor-not-allowed"
                        >
                            <ChevronRight className="h-5 w-5" aria-hidden="true" />
                        </button>
                    </nav>
                </div>
            </div>

            <CompareDrawer open={compareOpen} items={compareItems} onClose={() => setCompareOpen(false)} />
        </div>
    )
}
