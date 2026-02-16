import { useState, useEffect } from 'react'
import { api } from '@/api/client'
import { RunSummary } from '@/types/api'
import { Link } from 'react-router-dom'
import { Calendar, Clock, ChevronRight } from 'lucide-react'

export default function Runs() {
    const [runs, setRuns] = useState<RunSummary[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        async function fetchRuns() {
            try {
                const data = await api.runs.getRecent(50)
                setRuns(data)
            } catch (e) {
                console.error('Failed to fetch runs', e)
            } finally {
                setLoading(false)
            }
        }
        fetchRuns()
    }, [])

    if (loading) return <div className="p-8 text-center">Loading runs...</div>

    return (
        <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-6">Execution Runs</h1>

            <div className="bg-white shadow overflow-hidden rounded-md">
                <ul className="divide-y divide-gray-200">
                    {runs.map((run) => (
                        <li key={run.run_id}>
                            <Link to={`/runs/${run.run_id}`} className="block hover:bg-gray-50">
                                <div className="px-4 py-4 sm:px-6">
                                    <div className="flex items-center justify-between">
                                        <p className="text-sm font-medium text-indigo-600 truncate font-mono">{run.run_id}</p>
                                        <div className="ml-2 flex-shrink-0 flex">
                                            <p className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${run.status === 'COMPLETED' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                                                }`}>
                                                {run.status}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="mt-2 sm:flex sm:justify-between">
                                        <div className="sm:flex">
                                            <p className="flex items-center text-sm text-gray-500">
                                                <Calendar className="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" />
                                                {run.start_time ? new Date(run.start_time).toLocaleString() : 'Unknown Start'}
                                            </p>
                                            <p className="mt-2 flex items-center text-sm text-gray-500 sm:mt-0 sm:ml-6">
                                                <Clock className="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" />
                                                {run.end_time ? new Date(run.end_time).toLocaleString() : 'Running / Unknown'}
                                            </p>
                                        </div>
                                        <div className="mt-2 flex items-center text-sm text-gray-500 sm:mt-0">
                                            <p>
                                                {run.tickers.length > 0 ? (
                                                    <span className="truncate max-w-xs block">{run.tickers.join(', ')}</span>
                                                ) : 'All Components'}
                                            </p>
                                            <ChevronRight className="ml-2 h-5 w-5 text-gray-400" />
                                        </div>
                                    </div>
                                </div>
                            </Link>
                        </li>
                    ))}
                    {runs.length === 0 && (
                        <li className="px-4 py-8 text-center text-gray-500">No runs found.</li>
                    )}
                </ul>
            </div>
        </div>
    )
}
