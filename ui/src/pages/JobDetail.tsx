import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '@/api/client'
import { JobDetail as JobDetailType } from '@/types/api'
import LogViewer from '@/components/LogViewer'
import StatusBadge from '@/components/StatusBadge'

function fmt(ts: string | null | undefined): string {
    if (!ts) return '-'
    const d = new Date(ts)
    return Number.isNaN(d.getTime()) ? ts : d.toLocaleString()
}

export default function JobDetail() {
    const { jobId } = useParams<{ jobId: string }>()
    const [job, setJob] = useState<JobDetailType | null>(null)
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
                const meta = await api.jobs.getOne(jobId)
                setJob(meta)
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

    if (loading) return <div className="p-6 text-gray-500">Loading job detail...</div>
    if (error) return <div className="p-6 text-red-600">{error}</div>
    if (!job || !jobId) return <div className="p-6 text-gray-500">Job not found.</div>

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-gray-900">Job Detail</h1>
                <Link to="/jobs" className="text-sm text-indigo-700 hover:underline">
                    Back to Jobs
                </Link>
            </div>

            {job.status === 'FAILED' && (
                <section className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <h2 className="text-lg font-semibold text-red-800 mb-2">Error Summary</h2>
                    <div className="text-sm text-red-700">Exit Code: {job.exit_code ?? '-'}</div>
                    <div className="text-sm text-red-700 whitespace-pre-wrap">{job.error_message || 'No error message captured.'}</div>
                </section>
            )}

            <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
                <div className="text-sm"><span className="font-semibold">Job ID:</span> <span className="font-mono">{job.job_id}</span></div>
                <div className="text-sm"><span className="font-semibold">Type:</span> {job.job_type}</div>
                <div className="text-sm"><span className="font-semibold">Status:</span> <StatusBadge status={job.status} /></div>
                <div className="text-sm"><span className="font-semibold">Created:</span> {fmt(job.created_at)}</div>
                <div className="text-sm"><span className="font-semibold">Started:</span> {fmt(job.started_at)}</div>
                <div className="text-sm"><span className="font-semibold">Ended:</span> {fmt(job.ended_at)}</div>
                <div className="text-sm"><span className="font-semibold">Duration:</span> {job.duration_sec?.toFixed(1) ?? '-'} sec</div>
                <div className="text-sm"><span className="font-semibold">Exit Code:</span> {job.exit_code ?? '-'}</div>
                <div className="text-sm"><span className="font-semibold">CWD:</span> <span className="font-mono">{job.cwd}</span></div>
                <div className="text-sm"><span className="font-semibold">Command:</span> <span className="font-mono">{job.command.join(' ')}</span></div>
                <div className="text-sm"><span className="font-semibold">Args Preview:</span> <span className="font-mono">{job.args_preview}</span></div>
                <div className="text-sm"><span className="font-semibold">Runtime Meta:</span> <span className="font-mono">{job.runtime.meta_path}</span></div>
                <div className="text-sm"><span className="font-semibold">Runtime Log:</span> <span className="font-mono">{job.runtime.log_path}</span></div>

                {(job.artifacts?.run_id || job.artifacts?.bt_run_id) && (
                    <div className="pt-2 flex gap-2">
                        {job.artifacts?.run_id && (
                            <Link
                                to={`/runs/${job.artifacts.run_id}`}
                                className="px-3 py-1.5 text-sm text-white bg-indigo-600 rounded hover:bg-indigo-700"
                            >
                                View Run
                            </Link>
                        )}
                        {job.artifacts?.bt_run_id && (
                            <Link
                                to={`/backtests/${job.artifacts.bt_run_id}`}
                                className="px-3 py-1.5 text-sm text-white bg-indigo-600 rounded hover:bg-indigo-700"
                            >
                                View Backtest
                            </Link>
                        )}
                    </div>
                )}

                {job.artifacts?.artifacts_parse_error && (
                    <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                        {job.artifacts.artifacts_parse_error}
                    </div>
                )}
            </section>

            <LogViewer jobId={jobId} isRunning={isRunning} />
        </div>
    )
}