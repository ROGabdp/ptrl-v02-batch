import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/api/client'
import { JobRecord, JobStatus } from '@/types/api'

const STATUS_STYLES: Record<JobStatus, string> = {
    QUEUED: 'bg-gray-100 text-gray-700',
    RUNNING: 'bg-blue-100 text-blue-700',
    SUCCESS: 'bg-green-100 text-green-700',
    FAILED: 'bg-red-100 text-red-700',
}

function fmt(ts: string | null | undefined): string {
    if (!ts) return '-'
    const d = new Date(ts)
    return Number.isNaN(d.getTime()) ? ts : d.toLocaleString()
}

export default function Jobs() {
    const [jobs, setJobs] = useState<JobRecord[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const hasRunning = useMemo(
        () => jobs.some((j) => j.status === 'QUEUED' || j.status === 'RUNNING'),
        [jobs],
    )

    useEffect(() => {
        let timer: number | undefined

        const load = async () => {
            try {
                const data = await api.jobs.getRecent(100)
                setJobs(data)
                setError(null)
            } catch (e: any) {
                setError(e.message || 'Failed to load jobs')
            } finally {
                setLoading(false)
            }
        }

        load()
        timer = window.setInterval(load, hasRunning ? 3000 : 5000)

        return () => {
            if (timer) window.clearInterval(timer)
        }
    }, [hasRunning])

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-gray-900">Jobs</h1>
                <Link
                    to="/actions"
                    className="px-3 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700"
                >
                    New Action
                </Link>
            </div>

            {error && <div className="rounded-md bg-red-50 text-red-700 px-3 py-2 text-sm">{error}</div>}

            <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
                {loading ? (
                    <div className="p-6 text-gray-500">Loading jobs...</div>
                ) : jobs.length === 0 ? (
                    <div className="p-6 text-gray-500">No jobs yet.</div>
                ) : (
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Job ID</th>
                                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Type</th>
                                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Status</th>
                                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Started</th>
                                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Ended</th>
                                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Args</th>
                                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Jump</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {jobs.map((job) => (
                                <tr key={job.job_id} className="hover:bg-gray-50">
                                    <td className="px-4 py-3 text-sm font-mono text-indigo-700">
                                        <Link to={`/jobs/${job.job_id}`} className="hover:underline">
                                            {job.job_id}
                                        </Link>
                                    </td>
                                    <td className="px-4 py-3 text-sm text-gray-700">{job.job_type}</td>
                                    <td className="px-4 py-3 text-sm">
                                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold ${STATUS_STYLES[job.status]}`}>
                                            {job.status}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3 text-sm text-gray-600">{fmt(job.started_at)}</td>
                                    <td className="px-4 py-3 text-sm text-gray-600">{fmt(job.ended_at)}</td>
                                    <td className="px-4 py-3 text-xs font-mono text-gray-600 max-w-xl truncate">
                                        {job.command.join(' ')}
                                    </td>
                                    <td className="px-4 py-3 text-sm text-indigo-700 space-x-2">
                                        {job.artifacts_hint?.run_id && (
                                            <Link to={`/runs/${job.artifacts_hint.run_id}`} className="hover:underline">
                                                Run
                                            </Link>
                                        )}
                                        {job.artifacts_hint?.bt_run_id && (
                                            <Link to={`/backtests/${job.artifacts_hint.bt_run_id}`} className="hover:underline">
                                                Backtest
                                            </Link>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    )
}
