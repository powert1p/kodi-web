import { lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { RequireAuth, RequireGuest } from './features/auth/RequireAuth'

const HubPage = lazy(() => import('./features/hub/HubPage').then((module) => ({ default: module.HubPage })))
const LearningPathPage = lazy(() => import('./features/learning/LearningPathPage').then((module) => ({ default: module.LearningPathPage })))
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
                  <Route path="/" element={<LearningPathPage />} />
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
    <div className="flex min-h-dvh items-center bg-paper px-5" role="status" aria-label="Загружаем экран">
      <div className="tape-card mx-auto w-full max-w-3xl px-6 py-8">
        <div className="shimmer h-3 w-32 rounded-chip bg-paper-2" />
        <div className="shimmer mt-5 h-10 w-4/5 rounded-control bg-paper-2" />
        <div className="shimmer mt-3 h-10 w-2/3 rounded-control bg-paper-2" />
      </div>
    </div>
  )
  return standalone ? <main id="main-content">{content}</main> : content
}

export default App
