import { lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { RequireAuth, RequireGuest } from './features/auth/RequireAuth'
import './features/journey/JourneyPage.css'

const HubPage = lazy(() => import('./features/hub/HubPage').then((module) => ({ default: module.HubPage })))
const JourneyPage = lazy(() => import('./features/journey/JourneyPage').then((module) => ({ default: module.JourneyPage })))
const LearningPage = lazy(() => import('./features/learning/LearningPage').then((module) => ({ default: module.LearningPage })))
const DrillPage = lazy(() => import('./features/drill/DrillPage').then((module) => ({ default: module.DrillPage })))
const ClosurePage = lazy(() => import('./features/closure/ClosurePage').then((module) => ({ default: module.ClosurePage })))
const AnalyticsPage = lazy(() => import('./features/analytics/AnalyticsPage').then((module) => ({ default: module.AnalyticsPage })))
const SrezPage = lazy(() => import('./features/srez/SrezPage').then((module) => ({ default: module.SrezPage })))
const LoginPage = lazy(() => import('./features/auth/LoginPage').then((module) => ({ default: module.LoginPage })))
const NotFoundPage = lazy(() => import('./features/NotFoundPage').then((module) => ({ default: module.NotFoundPage })))

function App() {
  return (
    <Routes>
      {/* Публичный маршрут: /login → для гостей; авторизованных отправляет на Hub. */}
      <Route
        path="/login"
        element={
          <RequireGuest>
            <Suspense fallback={<RouteLoading standalone />}>
              <LoginPage />
            </Suspense>
          </RequireGuest>
        }
      />

      {/* Защищённые маршруты: без токена → /login. */}
      <Route
        path="/*"
        element={
          <RequireAuth>
            <AppShell>
              <Suspense fallback={<RouteLoading />}>
                <Routes>
                  <Route path="/" element={<JourneyPage />} />
                  <Route path="/lesson/:lessonId" element={<LearningPage />} />
                  <Route path="/review" element={<HubPage />} />
                  <Route path="/drill/:taskId" element={<DrillPage />} />
                  <Route path="/closure/:taskId" element={<ClosurePage />} />
                  <Route path="/analytics" element={<AnalyticsPage />} />
                  <Route path="/srez" element={<SrezPage />} />
                  <Route path="*" element={<NotFoundPage />} />
                </Routes>
              </Suspense>
            </AppShell>
          </RequireAuth>
        }
      />
    </Routes>
  )
}

function RouteLoading({ standalone = false }: { standalone?: boolean }) {
  const content = (
    <div className="journey-route-loading" role="status" aria-label="Загружаем экран">
      <span className="journey-route-loading__orb" />
      <span>Открываем твой маршрут…</span>
    </div>
  )
  return standalone ? <main id="main-content">{content}</main> : content
}

export default App
