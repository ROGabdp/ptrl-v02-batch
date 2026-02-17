import { useEffect, useMemo, useState } from 'react'
import { api } from '@/api/client'

interface LogViewerProps {
    jobId: string
    isRunning: boolean
}

export default function LogViewer({ jobId, isRunning }: LogViewerProps) {
    const [content, setContent] = useState('')
    const [nextOffset, setNextOffset] = useState(0)
    const [isTruncated, setIsTruncated] = useState(false)
    const [autoFollow, setAutoFollow] = useState(true)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const canPoll = useMemo(() => autoFollow && isRunning, [autoFollow, isRunning])

    const loadInitial = async () => {
        setLoading(true)
        try {
            const res = await api.jobs.getLog(jobId, { offset: 0, tail: 20000 })
            setContent(res.content)
            setNextOffset(res.next_offset)
            setIsTruncated(res.is_truncated)
            setError(null)
        } catch (e: any) {
            setError(e.message || 'Failed to load log')
        } finally {
            setLoading(false)
        }
    }

    const fetchIncremental = async () => {
        try {
            const res = await api.jobs.getLog(jobId, { offset: nextOffset })
            if (res.content) {
                setContent((prev) => prev + res.content)
            }
            setNextOffset(res.next_offset)
            setError(null)
        } catch (e: any) {
            setError(e.message || 'Failed to fetch log')
        }
    }

    useEffect(() => {
        setContent('')
        setNextOffset(0)
        setIsTruncated(false)
        setError(null)
        loadInitial()
    }, [jobId])

    useEffect(() => {
        if (!canPoll) return
        const timer = window.setInterval(() => {
            fetchIncremental()
        }, 1500)
        return () => window.clearInterval(timer)
    }, [canPoll, jobId, nextOffset])

    const onCopy = async () => {
        await navigator.clipboard.writeText(content)
    }

    return (
        <section className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3 gap-2">
                <h2 className="text-lg font-semibold text-gray-900">Log</h2>
                <div className="flex items-center gap-2">
                    <label className="inline-flex items-center gap-1 text-xs text-gray-600">
                        <input
                            type="checkbox"
                            checked={autoFollow}
                            onChange={(e) => setAutoFollow(e.target.checked)}
                        />
                        Auto-follow
                    </label>
                    <button
                        onClick={fetchIncremental}
                        className="px-3 py-1.5 text-sm font-medium border border-gray-300 rounded-md hover:bg-gray-50"
                    >
                        Refresh
                    </button>
                    <button
                        onClick={onCopy}
                        className="px-3 py-1.5 text-sm font-medium border border-gray-300 rounded-md hover:bg-gray-50"
                    >
                        Copy
                    </button>
                </div>
            </div>

            {isTruncated && (
                <div className="mb-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                    Log too long. Showing tail content first.
                </div>
            )}
            {error && <div className="mb-2 text-xs text-red-700">{error}</div>}

            <pre className="bg-gray-900 text-gray-100 p-3 rounded-md overflow-auto max-h-[520px] text-xs leading-5 font-mono whitespace-pre-wrap">
                {loading ? 'Loading log...' : content || '[empty log]'}
            </pre>
        </section>
    )
}