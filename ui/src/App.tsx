
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import Dashboard from '@/pages/Dashboard'
import Registry from '@/pages/Registry'
import Runs from '@/pages/Runs'
import RunDetail from '@/pages/RunDetail'
import Backtests from '@/pages/Backtests'
import BacktestDetail from '@/pages/BacktestDetail'

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
                </Routes>
            </Layout>
        </BrowserRouter>
    )
}

export default App
