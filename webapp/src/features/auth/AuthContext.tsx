// Контекст аутентификации: токен, вход, регистрация, выход.
// Провайдер оборачивает всё дерево приложения в main.tsx.

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { getToken, setToken, clearToken, loginWithPin, registerWithPin } from '../../lib/auth'

interface AuthContextValue {
  /** Текущий JWT-токен или null (неавторизован). */
  token: string | null
  /** Войти по номеру телефона и PIN. Сохраняет токен. */
  login: (phone: string, pin: string) => Promise<void>
  /** Зарегистрироваться с именем, PIN и согласием на фото. Сохраняет токен. */
  register: (phone: string, name: string, pin: string, photoConsent: boolean) => Promise<void>
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

  const login = useCallback(async (phone: string, pin: string) => {
    await loginWithPin(phone, pin)
    // После loginWithPin токен уже в localStorage — читаем оттуда.
    setTokenState(getToken())
  }, [])

  const register = useCallback(async (phone: string, name: string, pin: string, photoConsent: boolean) => {
    await registerWithPin(phone, name, pin, photoConsent)
    setTokenState(getToken())
  }, [])

  const logout = useCallback(() => {
    clearToken()
    setTokenState(null)
  }, [])

  // Если токен изменился снаружи (другой таб) — синхронизируем.
  // Простой подход: слушаем storage event.
  useState(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === 'kodi.jwt') {
        setTokenState(e.newValue)
        if (!e.newValue) clearToken()
        else setToken(e.newValue)
      }
    }
    window.addEventListener('storage', handler)
    return () => window.removeEventListener('storage', handler)
  })

  const value = useMemo<AuthContextValue>(
    () => ({ token, login, register, logout }),
    [token, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

/** Хук для получения контекста аутентификации. Обязателен внутри AuthProvider. */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth должен использоваться внутри AuthProvider')
  return ctx
}
