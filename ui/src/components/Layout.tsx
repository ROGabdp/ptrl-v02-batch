import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Activity, Database, LayoutDashboard, PlayCircle, GitBranch, Workflow, Calendar } from 'lucide-react'
import clsx from 'clsx'

export function Layout({ children }: { children: ReactNode }) {
    const location = useLocation()

    const navItems = [
        { path: '/', label: 'Dashboard', icon: LayoutDashboard },
        { path: '/daily', label: 'Daily', icon: Calendar },
        { path: '/registry', label: 'Registry', icon: Database },
        { path: '/runs', label: 'Runs', icon: Activity },
        { path: '/backtests', label: 'Backtests', icon: GitBranch },
        { path: '/jobs', label: 'Jobs', icon: Workflow },
        { path: '/actions', label: 'Actions', icon: PlayCircle },
    ]

    return (
        <div className="min-h-screen bg-gray-50 flex">
            <aside className="w-64 bg-white border-r border-gray-200 fixed h-full">
                <div className="h-16 flex items-center px-6 border-b border-gray-200">
                    <span className="text-xl font-bold text-indigo-600">PTRL v02</span>
                </div>
                <nav className="p-4 space-y-1">
                    {navItems.map((item) => {
                        const Icon = item.icon
                        const isActive =
                            location.pathname === item.path ||
                            (item.path !== '/' && location.pathname.startsWith(item.path))
                        return (
                            <Link
                                key={item.path}
                                to={item.path}
                                className={clsx(
                                    'flex items-center px-4 py-3 text-sm font-medium rounded-md transition-colors',
                                    isActive
                                        ? 'bg-indigo-50 text-indigo-700'
                                        : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900',
                                )}
                            >
                                <Icon className={clsx('mr-3 h-5 w-5', isActive ? 'text-indigo-600' : 'text-gray-400')} />
                                {item.label}
                            </Link>
                        )
                    })}
                </nav>
            </aside>

            <main className="flex-1 ml-64 p-8">
                <div className="max-w-7xl mx-auto">{children}</div>
            </main>
        </div>
    )
}
