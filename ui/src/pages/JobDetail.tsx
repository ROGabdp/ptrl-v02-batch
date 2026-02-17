import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '@/api/client'
import { JobRecord } from '@/types/api'

function fmt(ts: string | null | undefined): string {
    if (!ts) return '-'
    const d = new Date(ts)
    return Number.isNaN(d.getTime()) ? ts : d.toLocaleString()
}

export default function JobDetail() {
    const { jobId } = useParams<{ jobId: string }>()
    const [job, setJob] = useState<JobRecord | null>(null)
    const [logText, setLogText] = useState('')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const isRunning = useMemo(
        () => job?.status === 'QUEUED' || job?.status === 'RUNNING',
        [job?.status],
    )

    useEffect(() => {
        if (!jobId) return

        let timer: number | undefined

        const load = async () => {
            try {
                const [meta, log] = await Promise.all([api.jobs.getOne(jobId), api.jobs.getLog(jobId)])
                setJob(meta)
                setLogText(log)
                setError(null)
            } catch (e: any) {
                setError(e.message || 'Failed to load job detail')
            } finally {
                setLoading(false)
            }
        }

        load()
        timer = window.setInterval(load, isRunning ? 3000 : 5000)

        return () => {
            if (timer) window.clearInterval(timer)
        }
    }, [jobId, isRunning])

    const onCopy = async () => {
        await navigator.clipboard.writeText(logText)
    }

    if (loading) return <div className="p-6 text-gray-500">Loading job detail...</div>
    if (error) return <div className="p-6 text-red-600">{error}</div>
    if (!job) return <div className="p-6 text-gray-500">Job not found.</div>

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-gray-900">Job Detail</h1>
                <Link to="/jobs" className="text-sm text-indigo-700 hover:underline">
                    Back to Jobs
                </Link>
            </div>

            <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
                <div className="text-sm"><span className="font-semibold">Job ID:</span> <span className="font-mono">{job.job_id}</span></div>
                <div className="text-sm"><span className="font-semibold">Type:</span> {job.job_type}</div>
                <div className="text-sm"><span className="font-semibold">Status:</span> {job.status}</div>
                <div className="text-sm"><span className="font-semibold">Created:</span> {fmt(job.created_at)}</div>
                <div className="text-sm"><span className="font-semibold">Started:</span> {fmt(job.started_at)}</div>
                <div className="text-sm"><span className="font-semibold">Ended:</span> {fmt(job.ended_at)}</div>
                <div className="text-sm"><span className="font-semibold">CWD:</span> <span className="font-mono">{job.cwd}</span></div>
                <div className="text-sm"><span className="font-semibold">Command:</span> <span className="font-mono">{job.command.join(' ')}</span></div>
                {job.artifacts_hint?.run_id && (
                    <div className="text-sm">
                        <span className="font-semibold">Run:</span>{' '}
                        <Link to={`/runs/${job.artifacts_hint.run_id}`} className="text-indigo-700 hover:underline">
                            {job.artifacts_hint.run_id}
                        </Link>
                    </div>
                )}
                {job.artifacts_hint?.bt_run_id && (
                    <div className="text-sm">
                        <span className="font-semibold">Backtest:</span>{' '}
                        <Link to={`/backtests/${job.artifacts_hint.bt_run_id}`} className="text-indigo-700 hover:underline">
                            {job.artifacts_hint.bt_run_id}
                        </Link>
                    </div>
                )}
            </section>

            <section className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                    <h2 className="text-lg font-semibold text-gray-900">Log</h2>
                    <button
                        onClick={onCopy}
                        className="px-3 py-1.5 text-sm font-medium border border-gray-300 rounded-md hover:bg-gray-50"
                    >
                        Copy
                    </button>
                </div>
                <pre className="bg-gray-900 text-gray-100 p-3 rounded-md overflow-auto max-h-[520px] text-xs leading-5 font-mono whitespace-pre-wrap">
                    {logText || '[empty log]'}
                </pre>
            </section>
        </div>
    )
}
