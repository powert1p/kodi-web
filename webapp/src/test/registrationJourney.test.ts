import { createElement } from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../features/auth/AuthContext'
import { LoginPage } from '../features/auth/LoginPage'
import { RequireAuth, RequireGuest } from '../features/auth/RequireAuth'

function makeStorageMock(): Storage {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
    get length() { return Object.keys(store).length },
    key: (index: number) => Object.keys(store)[index] ?? null,
  } as Storage
}

const storageMock = makeStorageMock()

function RegistrationHarness() {
  return createElement(
    MemoryRouter,
    { initialEntries: ['/login'] },
    createElement(
      AuthProvider,
      null,
      createElement(
        Routes,
        null,
        createElement(Route, {
          path: '/login',
          element: createElement(RequireGuest, null, createElement(LoginPage)),
        }),
        createElement(Route, {
          path: '/',
          element: createElement(RequireAuth, null, createElement('h1', null, 'Начнём с тебя')),
        }),
      ),
    ),
  )
}

function jsonResponse(payload: unknown) {
  return {
    ok: true,
    status: 200,
    json: async () => payload,
  }
}

async function completeRegistration() {
  fireEvent.change(screen.getByRole('textbox', { name: 'Номер телефона' }), {
    target: { value: '+77019990001' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Продолжить' }))

  await screen.findByRole('heading', { name: 'Как тебя зовут?' })
  const nameField = screen.getByRole('textbox', { name: 'Имя' })
  await waitFor(() => expect(document.activeElement).toBe(nameField))
  fireEvent.change(nameField, {
    target: { value: 'Аян' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Далее' }))

  await screen.findByRole('heading', { name: 'В каком классе ты сейчас?' })
  const firstGrade = screen.getByRole('radio', { name: '4' })
  await waitFor(() => expect(document.activeElement).toBe(firstGrade))
  fireEvent.click(screen.getByRole('radio', { name: '7' }))
  fireEvent.click(screen.getByRole('button', { name: 'Далее' }))

  await screen.findByRole('heading', { name: 'Придумай PIN' })
  const pinField = screen.getByLabelText('Придумай PIN')
  await waitFor(() => expect(document.activeElement).toBe(pinField))
  fireEvent.change(pinField, {
    target: { value: '7319' },
  })
  fireEvent.click(screen.getByRole('button', { name: /Создать аккаунт/ }))
}

async function completeLogin() {
  fireEvent.change(screen.getByRole('textbox', { name: 'Номер телефона' }), {
    target: { value: '+77019990002' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Продолжить' }))

  await screen.findByRole('heading', { name: 'Добро пожаловать!' })
  const pinField = screen.getByLabelText('PIN-код')
  await waitFor(() => expect(document.activeElement).toBe(pinField))
  fireEvent.change(pinField, {
    target: { value: '7319' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Войти и продолжить урок' }))
}

describe('production journey нового ученика', () => {
  beforeEach(() => {
    storageMock.clear()
    vi.stubGlobal('localStorage', storageMock)
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    storageMock.clear()
  })

  it('объясняет потерю сети по-русски и оставляет регистрацию доступной для повтора', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    render(createElement(RegistrationHarness))
    const phoneField = screen.getByRole('textbox', { name: 'Номер телефона' })
    fireEvent.change(phoneField, { target: { value: '+77019990000' } })
    fireEvent.click(screen.getByRole('button', { name: 'Продолжить' }))

    expect((await screen.findByRole('alert')).textContent).toContain(
      'Не получилось подключиться. Проверь интернет и попробуй ещё раз.',
    )
    expect((phoneField as HTMLInputElement).disabled).toBe(false)
    expect((screen.getByRole('button', { name: 'Продолжить' }) as HTMLButtonElement).disabled).toBe(false)
  })

  it('после регистрации открывает адаптацию и не запрашивает старый learning path', async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url === '/api/auth/phone/check') return Promise.resolve(jsonResponse({ exists: false }))
      if (url === '/api/auth/phone/register') return Promise.resolve(jsonResponse({ access_token: 'new-student-token' }))
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(createElement(RegistrationHarness))
    await completeRegistration()

    expect(await screen.findByRole('heading', { name: 'Начнём с тебя' })).toBeTruthy()
    expect(fetchMock).not.toHaveBeenCalledWith('/api/learning/path/current', expect.anything())
  })

  it('созданный аккаунт не зависит от доступности старого learning path', async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url === '/api/auth/phone/check') return Promise.resolve(jsonResponse({ exists: false }))
      if (url === '/api/auth/phone/register') return Promise.resolve(jsonResponse({ access_token: 'new-student-token' }))
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(createElement(RegistrationHarness))
    await completeRegistration()

    expect(await screen.findByRole('heading', { name: 'Начнём с тебя' })).toBeTruthy()
    expect(localStorage.getItem('kodi.jwt')).toBe('new-student-token')
  })

  it('обычный вход отдаёт управление server-owned journey, а не lesson URL', async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url === '/api/auth/phone/check') return Promise.resolve(jsonResponse({ exists: true }))
      if (url === '/api/auth/phone/login') return Promise.resolve(jsonResponse({ access_token: 'returning-student-token' }))
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(createElement(RegistrationHarness))
    await completeLogin()

    expect(await screen.findByRole('heading', { name: 'Начнём с тебя' })).toBeTruthy()
    expect(fetchMock).not.toHaveBeenCalledWith('/api/learning/path/current', expect.anything())
  })
})
