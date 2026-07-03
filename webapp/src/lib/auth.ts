// Вспомогательные функции для хранения JWT-токена в localStorage.
// Используем ТОТ ЖЕ ключ 'kodi.jwt', что читает api.ts через authHeaders().

/** Ключ хранилища — должен совпадать с STORAGE_KEY в api.ts. */
const TOKEN_KEY = 'kodi.jwt'

/** Читает токен из localStorage. Возвращает null если нет или недоступен. */
export function getToken(): string | null {
  try {
    return typeof localStorage !== 'undefined'
      ? localStorage.getItem(TOKEN_KEY)
      : null
  } catch {
    return null
  }
}

/** Сохраняет токен в localStorage. */
export function setToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token)
  } catch {
    // Нет действий при недоступном хранилище (приватный режим браузера).
  }
}

/** Удаляет токен из localStorage (выход из аккаунта). */
export function clearToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY)
  } catch {
    // Нет действий при недоступном хранилище.
  }
}

// ——————————————————————————————————
// Типы ответов backend /auth/phone/*
// ——————————————————————————————————

/** Ответ /auth/phone/check: зарегистрирован ли номер. */
export interface PhoneCheckResponse {
  exists: boolean
}

/** Ответ /auth/phone/login и /auth/phone/register: access_token (JWT). */
export interface AuthTokenResponse {
  access_token: string
}

/** Профиль студента из /auth/me. */
export interface StudentProfile {
  id: number
  first_name: string | null
  last_name: string | null
  username: string | null
  full_name: string | null
  lang: string
  registered: boolean
  diagnostic_complete: boolean
  has_paused_diagnostic: boolean
  photo_consent: boolean | null
}

// ——————————————————————————————————
// API-функции аутентификации
// ——————————————————————————————————

const AUTH_BASE = '/api/auth/phone'

/** Проверяет, зарегистрирован ли номер телефона. */
export async function checkPhone(phone: string): Promise<PhoneCheckResponse> {
  const res = await fetch(`${AUTH_BASE}/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone }),
  })
  if (!res.ok) {
    const detail = await res.json().then((d: { detail?: string }) => d.detail).catch(() => null)
    throw new Error(detail ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<PhoneCheckResponse>
}

/** Вход по номеру телефона и PIN-коду. Сохраняет токен в localStorage. */
export async function loginWithPin(phone: string, pin: string): Promise<void> {
  const res = await fetch(`${AUTH_BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone, pin }),
  })
  if (!res.ok) {
    const detail = await res.json().then((d: { detail?: string }) => d.detail).catch(() => null)
    throw new Error(detail ?? `HTTP ${res.status}`)
  }
  const data = (await res.json()) as AuthTokenResponse
  setToken(data.access_token)
}

/** Регистрация нового студента. Сохраняет токен в localStorage. */
export async function registerWithPin(phone: string, name: string, pin: string, photoConsent: boolean): Promise<void> {
  const res = await fetch(`${AUTH_BASE}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone, name, pin, photo_consent: photoConsent }),
  })
  if (!res.ok) {
    const detail = await res.json().then((d: { detail?: string }) => d.detail).catch(() => null)
    throw new Error(detail ?? `HTTP ${res.status}`)
  }
  const data = (await res.json()) as AuthTokenResponse
  setToken(data.access_token)
}

/** DEV-фикстура профиля (бэкенд недоступен локально) — photo_consent: null, чтобы ConsentCard было чем демонстрировать. */
const MOCK_PROFILE: StudentProfile = {
  id: 1,
  first_name: 'Айдана',
  last_name: null,
  username: null,
  full_name: 'Айдана',
  lang: 'ru',
  registered: true,
  diagnostic_complete: true,
  has_paused_diagnostic: false,
  photo_consent: null,
}

/**
 * Получает профиль текущего студента (/auth/me) — источник photo_consent для consent-UI.
 * В DEV (не в тестах): бэкенд недоступен/упал → подставляем фикстуру (тот же паттерн, что
 * и в fetchWrongTasks).
 */
export async function fetchMe(): Promise<StudentProfile> {
  const token = getToken()
  try {
    const res = await fetch('/api/auth/me', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return res.json() as Promise<StudentProfile>
  } catch (err) {
    if (import.meta.env.DEV && import.meta.env.MODE !== 'test') {
      return MOCK_PROFILE
    }
    throw err
  }
}
