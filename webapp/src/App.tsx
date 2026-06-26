import { Routes, Route } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { HubPage } from './features/hub/HubPage'
import { DrillPage } from './features/drill/DrillPage'
import { ClosurePage } from './features/closure/ClosurePage'
import { AnalyticsPage } from './features/analytics/AnalyticsPage'

function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<HubPage />} />
        <Route path="/drill/:taskId" element={<DrillPage />} />
        <Route path="/closure/:taskId" element={<ClosurePage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
      </Routes>
    </AppShell>
  )
}

export default App
