// Контекст аутентификации: токен, вход, регистрация, выход.
// Провайдер оборачивает всё дерево приложения в main.tsx.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { clearToken, getToken, loginWithPin, registerWithPin, subscribeToken } from '../../lib/auth'

interface AuthContextValue {
  /** Текущий JWT-токен или null (неавторизован). */
  token: string | null
  /** Войти по номеру телефона и PIN. Сохраняет токен. */
  login: (phone: string, pin: string) => Promise<void>
  /** Зарегистрироваться с именем, классом (4–7) и PIN. Сохраняет токен. */
  register: (phone: string, name: string, pin: string, grade: number | null) => Promise<void>
  /** Маршрут, куда RequireGuest переводит после завершённой auth-операции. */
  authDestination: string
  /** Выйти из аккаунта (удаляет токен). */
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  // Инициализируем из localStorage при монтировании.
  const [token, setTokenState] = useState<string | null>(() => getToken())
  const [authDestination, setAuthDestination] = useState('/')

  const login = useCallback(async (phone: string, pin: string) => {
    await loginWithPin(phone, pin)
    setAuthDestination('/')
    setTokenState(getToken())
  }, [])

  const register = useCallback(async (phone: string, name: string, pin: string, grade: number | null) => {
    await registerWithPin(phone, name, pin, grade)
    setAuthDestination('/')
    setTokenState(getToken())
  }, [])

  const logout = useCallback(() => {
    clearToken()
    setAuthDestination('/')
    setTokenState(null)
  }, [])

  // Синхронизируем logout при 401, same-tab login и изменения из другой вкладки.
  useEffect(() => {
    return subscribeToken(() => {
      setAuthDestination('/')
      setTokenState(getToken())
    })
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({ token, login, register, authDestination, logout }),
    [token, login, register, authDestination, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

/** Хук для получения контекста аутентификации. Обязателен внутри AuthProvider. */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth должен использоваться внутри AuthProvider')
  return ctx
}
