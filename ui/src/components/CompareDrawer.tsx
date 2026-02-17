import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { RegistryModelRow } from '@/types/api'

interface CompareDrawerProps {
    open: boolean
    items: RegistryModelRow[]
    onClose: () => void
}

function pct(v?: number): string {
    if (v === undefined || v === null) return '-'
    return `${(v * 100).toFixed(1)}%`
}

function num(v?: number, d = 3): string {
    if (v === undefined || v === null) return '-'
    return v.toFixed(d)
}

function intVal(v?: number): string {
    if (v === undefined || v === null) return '-'
    return `${Math.trunc(v)}`
}

function labelText(horizon?: number, threshold?: number): string {
    const h = horizon === undefined || horizon === null ? '-' : `${horizon}d`
    if (threshold === undefined || threshold === null) return `${h} / -`
    const t = threshold * 100
    const tStr = Number.isInteger(t) ? `${t.toFixed(0)}%` : `${t.toFixed(1)}%`
    return `${h} / ${tStr}`
}

const COMPARE_GUARDRAIL =
    'Compare \u5141\u8a31\u8de8 ticker / \u8de8 label\u3002\u8de8 ticker \u6642 precision \u53ef\u80fd\u53d7\u4e8b\u4ef6\u6bd4\u4f8b\uff08positive_rate\uff09\u5f71\u97ff\uff0c\u8acb\u4e00\u8d77\u770b lift\u3001positive_rate\u3001buy_rate \u8207 support\uff0c\u907f\u514d base-rate \u8aa4\u8b80\u3002'

const CROSS_TICKER_HINT = '\u76ee\u524d\u9078\u53d6\u5305\u542b\u591a\u500b ticker\u3002'

export default function CompareDrawer({ open, items, onClose }: CompareDrawerProps) {
    const sortedItems = useMemo(() => {
        const copied = [...items]
        copied.sort((a, b) => {
            const tickerCmp = (a.ticker || '').localeCompare(b.ticker || '')
            if (tickerCmp !== 0) return tickerCmp
            const horizonA = a.label_horizon_days ?? Number.MAX_SAFE_INTEGER
            const horizonB = b.label_horizon_days ?? Number.MAX_SAFE_INTEGER
            if (horizonA !== horizonB) return horizonA - horizonB
            const thresholdA = a.label_threshold ?? Number.MAX_SAFE_INTEGER
            const thresholdB = b.label_threshold ?? Number.MAX_SAFE_INTEGER
            return thresholdA - thresholdB
        })
        return copied
    }, [items])

    const isCrossTicker = useMemo(() => new Set(items.map((it) => it.ticker)).size > 1, [items])

    if (!open) return null

    return (
        <div className="fixed inset-0 z-50">
            <div className="absolute inset-0 bg-black/30" onClick={onClose} />
            <aside className="absolute right-0 top-0 h-full w-full max-w-5xl bg-white shadow-xl border-l border-gray-200 p-4 overflow-auto">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-gray-900">Compare Models ({items.length})</h2>
                    <button onClick={onClose} className="px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50">
                        Close
                    </button>
                </div>

                {items.length > 0 && (
                    <div className="mb-4 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                        <p>{COMPARE_GUARDRAIL}</p>
                        {isCrossTicker && <p className="mt-1 text-xs text-amber-800">{CROSS_TICKER_HINT}</p>}
                    </div>
                )}

                <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                        <thead>
                            <tr className="border-b border-gray-200 text-left text-gray-500">
                                <th className="py-2 pr-4">Ticker</th>
                                <th className="py-2 pr-4">Run ID</th>
                                <th className="py-2 pr-4">Mode</th>
                                <th className="py-2 pr-4">Label</th>
                                <th className="py-2 pr-4">Precision</th>
                                <th className="py-2 pr-4">Lift</th>
                                <th className="py-2 pr-4">Buy Rate</th>
                                <th className="py-2 pr-4">Positive Rate</th>
                                <th className="py-2 pr-4">Support</th>
                                <th className="py-2 pr-4">TP</th>
                                <th className="py-2 pr-4">FP</th>
                                <th className="py-2 pr-4">TN</th>
                                <th className="py-2 pr-4">FN</th>
                            </tr>
                        </thead>
                        <tbody>
                            {sortedItems.map((it, idx) => (
                                <tr key={`${it.ticker}-${it.run_id}-${idx}`} className="border-b border-gray-100 align-top">
                                    <td className="py-2 pr-4 font-semibold text-gray-900">{it.ticker}</td>
                                    <td className="py-2 pr-4 font-mono text-xs text-gray-700">
                                        <Link to={`/runs/${it.run_id}`} className="text-indigo-600 hover:text-indigo-900 hover:underline">
                                            {it.run_id}
                                        </Link>
                                    </td>
                                    <td className="py-2 pr-4 text-gray-700">{it.mode || '-'}</td>
                                    <td className="py-2 pr-4 text-gray-700">{labelText(it.label_horizon_days, it.label_threshold)}</td>
                                    <td className="py-2 pr-4 text-gray-700">{pct(it.precision)}</td>
                                    <td className="py-2 pr-4 text-gray-700">{num(it.lift, 3)}</td>
                                    <td className="py-2 pr-4 text-gray-700">{pct(it.buy_rate)}</td>
                                    <td className="py-2 pr-4 text-gray-700">{pct(it.positive_rate)}</td>
                                    <td className="py-2 pr-4 text-gray-700">{intVal(it.support)}</td>
                                    <td className="py-2 pr-4 text-gray-700">{intVal(it.tp)}</td>
                                    <td className="py-2 pr-4 text-gray-700">{intVal(it.fp)}</td>
                                    <td className="py-2 pr-4 text-gray-700">{intVal(it.tn)}</td>
                                    <td className="py-2 pr-4 text-gray-700">{intVal(it.fn)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </aside>
        </div>
    )
}
