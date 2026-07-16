// Гард маршрутов: неавторизованных редиректит на /login.
// Авторизованных на /login редиректит на / (Hub).

import { Navigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from './AuthContext'

interface RequireAuthProps {
  children: ReactNode
}

/** Оборачивает защищённые маршруты. Без токена → /login. */
export function RequireAuth({ children }: RequireAuthProps) {
  const { token } = useAuth()
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

/** Обёртка для /login: если уже авторизован → Hub. */
export function RequireGuest({ children }: RequireAuthProps) {
  const { token, authDestination } = useAuth()
  if (token) return <Navigate to={authDestination} replace />
  return <>{children}</>
}
