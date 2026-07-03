import { Routes, Route } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { HubPage } from './features/hub/HubPage'
import { DrillPage } from './features/drill/DrillPage'
import { ClosurePage } from './features/closure/ClosurePage'
import { AnalyticsPage } from './features/analytics/AnalyticsPage'
import { SrezPage } from './features/srez/SrezPage'
import { LoginPage } from './features/auth/LoginPage'
import { RequireAuth, RequireGuest } from './features/auth/RequireAuth'

function App() {
  return (
    <Routes>
      {/* Публичный маршрут: /login → для гостей; авторизованных отправляет на Hub. */}
      <Route
        path="/login"
        element={
          <RequireGuest>
            <LoginPage />
          </RequireGuest>
        }
      />

      {/* Защищённые маршруты: без токена → /login. */}
      <Route
        path="/*"
        element={
          <RequireAuth>
            <AppShell>
              <Routes>
                <Route path="/" element={<HubPage />} />
                <Route path="/drill/:taskId" element={<DrillPage />} />
                <Route path="/closure/:taskId" element={<ClosurePage />} />
                <Route path="/analytics" element={<AnalyticsPage />} />
                <Route path="/srez" element={<SrezPage />} />
              </Routes>
            </AppShell>
          </RequireAuth>
        }
      />
    </Routes>
  )
}

export default App
