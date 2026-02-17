import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import Actions from '@/pages/Actions'
import BacktestDetail from '@/pages/BacktestDetail'
import Backtests from '@/pages/Backtests'
import Dashboard from '@/pages/Dashboard'
import JobDetail from '@/pages/JobDetail'
import Jobs from '@/pages/Jobs'
import Registry from '@/pages/Registry'
import RunDetail from '@/pages/RunDetail'
import Runs from '@/pages/Runs'

function App() {
    return (
        <BrowserRouter>
            <Layout>
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/registry" element={<Registry />} />
                    <Route path="/runs" element={<Runs />} />
                    <Route path="/runs/:runId" element={<RunDetail />} />
                    <Route path="/backtests" element={<Backtests />} />
                    <Route path="/backtests/:btId" element={<BacktestDetail />} />
                    <Route path="/jobs" element={<Jobs />} />
                    <Route path="/jobs/:jobId" element={<JobDetail />} />
                    <Route path="/actions" element={<Actions />} />
                </Routes>
            </Layout>
        </BrowserRouter>
    )
}

export default App
