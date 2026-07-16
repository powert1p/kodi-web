import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { registerSW } from 'virtual:pwa-register'
import './index.css'
import App from './App.tsx'
import { AuthProvider } from './features/auth/AuthContext.tsx'
import { retireLegacyFlutterServiceWorker } from './lib/legacyServiceWorker.ts'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
})

// Сначала снимаем legacy root-scope Flutter SW, затем регистрируем текущий /app/ PWA.
async function startServiceWorker(): Promise<void> {
  try {
    await retireLegacyFlutterServiceWorker()
  } catch {
    // Ошибка миграции не должна блокировать запуск приложения и его нового SW.
  }
  registerSW({ immediate: true })
}

void startServiceWorker()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename="/app">
        {/* AuthProvider читает токен из localStorage при старте */}
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
