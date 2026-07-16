// Тесты: хранилище токенов + auth API-функции.
// fetch мокается глобально; localStorage заменяется in-memory мок-реализацией.

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { getToken, setToken, clearToken, loginWithPin, registerWithPin } from '../lib/auth'
import type { AuthTokenResponse } from '../lib/auth'
import { ApiError } from '../lib/api'

// ——————————————————————————————————
// In-memory мок localStorage
// (vitest 4.x VM-изоляция не даёт полноценный DOM localStorage)
// ——————————————————————————————————
function makeStorageMock(): Storage {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, val: string) => { store[key] = val },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
    get length() { return Object.keys(store).length },
    key: (i: number) => Object.keys(store)[i] ?? null,
  } as Storage
}

const storageMock = makeStorageMock()

beforeEach(() => {
  storageMock.clear()
  vi.stubGlobal('localStorage', storageMock)
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

// ——————————————————————————————————
// Token helpers: set / get / clear
// ——————————————————————————————————

describe('token helpers', () => {
  it('getToken() возвращает null если токена нет', () => {
    expect(getToken()).toBeNull()
  })

  it('setToken() + getToken() — round-trip', () => {
    setToken('test.jwt.token')
    expect(getToken()).toBe('test.jwt.token')
  })

  it('clearToken() удаляет токен', () => {
    setToken('to-be-deleted')
    clearToken()
    expect(getToken()).toBeNull()
  })

  it('повторный setToken перезаписывает предыдущий', () => {
    setToken('first')
    setToken('second')
    expect(getToken()).toBe('second')
  })

  it('ключ совпадает с "kodi.jwt" — тот же что api.ts', () => {
    setToken('shared-key-check')
    // Прямой доступ к localStorage с тем же ключом — должны совпадать.
    expect(localStorage.getItem('kodi.jwt')).toBe('shared-key-check')
  })
})

// ——————————————————————————————————
// loginWithPin: успех
// ——————————————————————————————————

describe('loginWithPin', () => {
  it('вызывает /api/auth/phone/login с правильным телом и сохраняет токен', async () => {
    const mockToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.live'
    const mockResponse: AuthTokenResponse = { access_token: mockToken }

    let capturedBody: Record<string, string> | null = null
    vi.stubGlobal('fetch', vi.fn().mockImplementation((_url: string, init: RequestInit) => {
      capturedBody = JSON.parse(init.body as string) as Record<string, string>
      return Promise.resolve({
        ok: true,
        json: async () => mockResponse,
      })
    }))

    await loginWithPin('+77001234567', '1234')

    // Правильный URL.
    const fetchMock = vi.mocked(fetch)
    const [url] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/auth/phone/login')

    // Правильные поля тела.
    expect(capturedBody?.['phone']).toBe('+77001234567')
    expect(capturedBody?.['pin']).toBe('1234')

    // Токен сохранён в localStorage.
    expect(getToken()).toBe(mockToken)
  })

  it('бросает Error с detail при 401 (неверный PIN)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Неверный номер телефона или PIN' }),
    }))

    await expect(loginWithPin('+77000000000', '0000')).rejects.toThrow(
      'Неверный номер телефона или PIN',
    )
    // Токен не должен быть сохранён.
    expect(getToken()).toBeNull()
  })

  it('бросает Error с HTTP-кодом если detail отсутствует', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({}),
    }))

    await expect(loginWithPin('+7000', '0000')).rejects.toThrow('HTTP 500')
    expect(getToken()).toBeNull()
  })
})

// ——————————————————————————————————
// registerWithPin: успех
// ——————————————————————————————————

describe('registerWithPin', () => {
  it('вызывает /api/auth/phone/register с phone, name, pin и сохраняет токен', async () => {
    const mockToken = 'new.student.token'
    let capturedBody: Record<string, string> | null = null

    vi.stubGlobal('fetch', vi.fn().mockImplementation((_url: string, init: RequestInit) => {
      capturedBody = JSON.parse(init.body as string) as Record<string, string>
      return Promise.resolve({
        ok: true,
        json: async () => ({ access_token: mockToken }),
      })
    }))

    await registerWithPin('+77009876543', 'Айдана', '5678', 7)

    const fetchMock = vi.mocked(fetch)
    const [url] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/auth/phone/register')
    expect(capturedBody?.['phone']).toBe('+77009876543')
    expect(capturedBody?.['name']).toBe('Айдана')
    expect(capturedBody?.['pin']).toBe('5678')
    expect(capturedBody?.['grade']).toBe(7)
    expect(capturedBody).not.toHaveProperty('photo_consent')
    expect(getToken()).toBe(mockToken)
  })

  it('бросает Error при 409 (номер уже зарегистрирован)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ detail: 'Этот номер уже зарегистрирован' }),
    }))

    await expect(registerWithPin('+77001234567', 'Test', '1234')).rejects.toThrow(
      'Этот номер уже зарегистрирован',
    )
    expect(getToken()).toBeNull()
  })
})

// ——————————————————————————————————
// ApiError импортирован из api.ts — проверяем статус
// ——————————————————————————————————

describe('ApiError из api.ts', () => {
  it('сохраняет status и name', () => {
    const err = new ApiError(422, 'Validation error')
    expect(err.status).toBe(422)
    expect(err.name).toBe('ApiError')
    expect(err.message).toBe('Validation error')
  })
})
