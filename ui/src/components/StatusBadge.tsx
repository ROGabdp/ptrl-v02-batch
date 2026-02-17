import { JobStatus } from '@/types/api'

const STATUS_STYLES: Record<JobStatus, string> = {
    QUEUED: 'bg-gray-100 text-gray-700',
    RUNNING: 'bg-blue-100 text-blue-700',
    SUCCESS: 'bg-green-100 text-green-700',
    FAILED: 'bg-red-100 text-red-700',
}

export default function StatusBadge({ status }: { status: JobStatus }) {
    return (
        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold ${STATUS_STYLES[status]}`}>
            {status}
        </span>
    )
}