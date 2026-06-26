// Типизированный HTTP-клиент для «Работы над ошибками».
// Хуки TanStack Query поверх raw-функций; mock-fallback для DEV.
// Bearer JWT берётся из localStorage по ключу STORAGE_KEY.

import { useQuery, useMutation } from '@tanstack/react-query'
import type { WrongTask, Diagnosis, AnalyticsData } from './types'
import { MOCK_WRONG_TASKS } from '../features/hub/mock'
import { MOCK_ANALYTICS } from '../features/analytics/mock'

/** Ключ хранилища JWT-токена. */
const STORAGE_KEY = 'kodi.jwt'

/** Базовый URL API — relative same-origin (nginx проксирует /api/ на backend). */
const API_BASE = '/api'

// ——————————————————————————————————
// Кастомные ошибки
// ——————————————————————————————————

/** HTTP-ошибка (не-2xx статус). */
export class ApiError extends Error {
  // erasableSyntaxOnly запрещает parameter properties — объявляем поле явно.
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

/** Сетевая ошибка (fetch rejected / offline). */
export class NetworkError extends Error {
  constructor(cause: unknown) {
    super(cause instanceof Error ? cause.message : 'Network error')
    this.name = 'NetworkError'
    if (cause instanceof Error) this.cause = cause
  }
}

// ——————————————————————————————————
// Утилиты
// ——————————————————————————————————

/** Формирует заголовки запроса: Authorization (если JWT есть) + Accept. */
function authHeaders(): Record<string, string> {
  let token: string | null = null
  try {
    token = typeof localStorage !== 'undefined' && typeof localStorage.getItem === 'function'
      ? localStorage.getItem(STORAGE_KEY)
      : null
  } catch {
    // localStorage может быть недоступен в тестовой или server-side среде
  }
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

/**
 * Выполняет fetch с обработкой сетевых ошибок и не-2xx статусов.
 * Бросает NetworkError при rejected или ApiError при не-2xx.
 */
async function apiFetch(url: string, init?: RequestInit): Promise<Response> {
  let res: Response
  try {
    res = await fetch(url, init)
  } catch (err) {
    throw new NetworkError(err)
  }
  if (!res.ok) throw new ApiError(res.status, `HTTP ${res.status}: ${url}`)
  return res
}

// ——————————————————————————————————
// Raw-функции (напрямую тестируемы без рендера)
// ——————————————————————————————————

/**
 * Получить список задач с ошибками.
 * В DEV: если API вернул пустой массив или упал — подставляем mock-фикстуру.
 *
 * @param days — фильтр по дням (необязательно)
 * @param limit — лимит задач (необязательно)
 */
export async function fetchWrongTasks(days?: number, limit?: number): Promise<WrongTask[]> {
  const params = new URLSearchParams()
  if (days !== undefined) params.set('days', String(days))
  if (limit !== undefined) params.set('limit', String(limit))
  const qs = params.toString() ? `?${params.toString()}` : ''

  try {
    const res = await apiFetch(`${API_BASE}/trainer/wrong-tasks${qs}`, {
      headers: authHeaders(),
    })
    const data = (await res.json()) as { tasks: WrongTask[] }
    const tasks = data.tasks ?? []

    // DEV mock-fallback (не в тестах): пустой ответ → показываем фикстуру
    if (import.meta.env.DEV && import.meta.env.MODE !== 'test' && tasks.length === 0) {
      return MOCK_WRONG_TASKS
    }
    return tasks
  } catch (err) {
    // В DEV (не в тестах) подставляем мок при ЛЮБОЙ ошибке — бэкенд недоступен,
    // 404 от vite-сервера или HTML вместо JSON. В тестах (MODE=test) всегда
    // пробрасываем, чтобы тест мог проверить поведение.
    if (import.meta.env.DEV && import.meta.env.MODE !== 'test') {
      return MOCK_WRONG_TASKS
    }
    throw err
  }
}

/**
 * Получить аналитику по тренажёру (топ повторяющихся ошибок).
 * В DEV (не в тестах): пустой ответ или NetworkError → подставляем mock-фикстуру,
 * чтобы экран «Прогресс» был демонстрируем без живого бэка. Тесты (MODE=test)
 * всегда получают сырой ответ — fallback их не трогает.
 */
export async function fetchAnalytics(): Promise<unknown> {
  const devFallback = import.meta.env.DEV && import.meta.env.MODE !== 'test'
  try {
    const res = await apiFetch(`${API_BASE}/trainer/analytics`, {
      headers: authHeaders(),
    })
    const data = (await res.json()) as Partial<AnalyticsData> | null
    if (devFallback && (!data || !data.error_types || data.error_types.length === 0)) {
      return MOCK_ANALYTICS
    }
    return data
  } catch (err) {
    // В DEV эндпоинт ещё не построен → 404 (ApiError) или offline (NetworkError)
    // одинаково подставляют мок, чтобы экран был демонстрируем. Тесты не трогаем.
    if (devFallback && (err instanceof NetworkError || err instanceof ApiError)) {
      return MOCK_ANALYTICS
    }
    throw err
  }
}

/** Нормализует unknown-ответ аналитики в типизированный AnalyticsData (или null). */
export function asAnalyticsData(raw: unknown): AnalyticsData | null {
  if (!raw || typeof raw !== 'object') return null
  const types = (raw as { error_types?: unknown }).error_types
  if (!Array.isArray(types)) return null
  return { error_types: types as AnalyticsData['error_types'] }
}

/** Параметры запроса диагноза ошибки. */
export interface DiagnoseParams {
  problem_id: number
  attempt_id?: number
  photo: File | Blob
}

/**
 * Отправить фото решения для диагностики ошибки.
 * Тело запроса — multipart/form-data (поля: problem_id, attempt_id?, photo).
 */
export async function postDiagnose(params: DiagnoseParams): Promise<Diagnosis> {
  const form = new FormData()
  form.append('problem_id', String(params.problem_id))
  if (params.attempt_id !== undefined) {
    form.append('attempt_id', String(params.attempt_id))
  }
  form.append('photo', params.photo)

  const res = await apiFetch(`${API_BASE}/trainer/diagnose`, {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  })
  return res.json() as Promise<Diagnosis>
}

// ——————————————————————————————————
// TanStack Query хуки
// ——————————————————————————————————

/** Хук: список задач с ошибками (с кэшем 60 с). */
export function useWrongTasks(days?: number, limit?: number) {
  return useQuery({
    queryKey: ['wrong-tasks', days, limit],
    queryFn: () => fetchWrongTasks(days, limit),
    staleTime: 60_000,
  })
}

/**
 * Хук-селектор: одна задача по id из кэша wrong-tasks.
 * Переиспользует тот же queryKey — не делает отдельный запрос.
 * @returns задача или undefined (загрузка / не найдена)
 */
export function useWrongTask(id: string) {
  return useQuery({
    queryKey: ['wrong-tasks', undefined, undefined],
    queryFn: () => fetchWrongTasks(),
    staleTime: 60_000,
    select: (tasks: WrongTask[]) => tasks.find((t) => t.id === id),
  })
}

/** Хук: аналитика тренажёра. */
export function useAnalytics() {
  return useQuery({
    queryKey: ['trainer-analytics'],
    queryFn: fetchAnalytics,
    staleTime: 300_000,
  })
}

/** Хук-мутация: диагностика ошибки по фото. */
export function useDiagnose() {
  return useMutation({
    mutationFn: (params: DiagnoseParams) => postDiagnose(params),
  })
}
