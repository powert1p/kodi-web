// Типизированный HTTP-клиент для «Работы над ошибками».
// Хуки TanStack Query поверх raw-функций; mock-fallback для DEV.
// Bearer JWT берётся из localStorage по ключу STORAGE_KEY.

import { useQuery, useMutation } from '@tanstack/react-query'
import type { WrongTask, Diagnosis, AnalyticsData, ProblemTopic, TutorChatResponse, VerificationProblemDTO, SrezTask, StepVerdict } from './types'
import { MOCK_WRONG_TASKS } from '../features/hub/mock'

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
 * Результат /wrong-tasks: список ошибок + флаг активности.
 * has_activity разводит два пустых состояния hub: false → новичок (онбординг),
 * true + пустой список → ветеран (всё разобрано). Зеркалит BE WrongTasksResponse.
 */
export interface WrongTasksResult {
  tasks: WrongTask[]
  has_activity: boolean
}

/**
 * Получить список задач с ошибками + признак активности ученика.
 * В DEV: если бэкенд недоступен/упал — подставляем mock-фикстуру.
 *
 * @param days — фильтр по дням (необязательно)
 * @param limit — лимит задач (необязательно)
 */
export async function fetchWrongTasks(days?: number, limit?: number): Promise<WrongTasksResult> {
  const params = new URLSearchParams()
  if (days !== undefined) params.set('days', String(days))
  if (limit !== undefined) params.set('limit', String(limit))
  const qs = params.toString() ? `?${params.toString()}` : ''

  try {
    const res = await apiFetch(`${API_BASE}/trainer/wrong-tasks${qs}`, {
      headers: authHeaders(),
    })
    const data = (await res.json()) as { tasks?: WrongTask[]; has_activity?: boolean }
    const tasks = data.tasks ?? []

    // DEV mock-fallback (не в тестах): показываем демо-фикстуру ТОЛЬКО когда бэкенд
    // НЕ сообщил has_activity — это старая форма ответа или замоканный {tasks:[]}
    // (бэка нет). Новый ответ с has_activity — источник истины: пустой список у
    // новичка (has_activity=false) честно ведёт в онбординг, мок его НЕ подменяет.
    if (
      import.meta.env.DEV &&
      import.meta.env.MODE !== 'test' &&
      tasks.length === 0 &&
      data.has_activity === undefined
    ) {
      return { tasks: MOCK_WRONG_TASKS, has_activity: true }
    }
    return { tasks, has_activity: data.has_activity ?? false }
  } catch (err) {
    // В DEV (не в тестах) подставляем мок при ЛЮБОЙ ошибке — бэкенд недоступен,
    // 404 от vite-сервера или HTML вместо JSON. В тестах (MODE=test) всегда
    // пробрасываем, чтобы тест мог проверить поведение.
    if (import.meta.env.DEV && import.meta.env.MODE !== 'test') {
      return { tasks: MOCK_WRONG_TASKS, has_activity: true }
    }
    throw err
  }
}

/**
 * Получить аналитику по тренажёру (топ повторяющихся ошибок).
 * Возвращает сырой JSON — нормализация в типизированный AnalyticsData через asAnalyticsData.
 */
export async function fetchAnalytics(): Promise<unknown> {
  const res = await apiFetch(`${API_BASE}/trainer/analytics`, { headers: authHeaders() })
  return res.json()
}

/** Нормализует unknown-ответ аналитики в AnalyticsData (или null). */
export function asAnalyticsData(raw: unknown): AnalyticsData | null {
  if (!raw || typeof raw !== 'object') return null
  const myTop = (raw as { my_top?: unknown }).my_top
  if (!Array.isArray(myTop)) return null
  const globalTop = (raw as { global_top?: unknown }).global_top
  return {
    my_top: myTop as AnalyticsData['my_top'],
    global_top: Array.isArray(globalTop) ? (globalTop as AnalyticsData['global_top']) : undefined,
  }
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

/** Параметры запроса проверки одного шага лесенки (Блок 1.2). */
export interface StepSubmitParams {
  decomp_idx: number
  step_n: number
  problem_id?: number
  photo: File | Blob
}

/**
 * Отправить фото одного шага лесенки для узкой vision-проверки.
 * Тело запроса — multipart/form-data (поля: decomp_idx, step_n, problem_id?, photo).
 */
export async function postStepSubmit(params: StepSubmitParams): Promise<StepVerdict> {
  const form = new FormData()
  form.append('decomp_idx', String(params.decomp_idx))
  form.append('step_n', String(params.step_n))
  if (params.problem_id !== undefined) form.append('problem_id', String(params.problem_id))
  form.append('photo', params.photo)

  const res = await apiFetch(`${API_BASE}/trainer/step-submit`, {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  })
  return res.json() as Promise<StepVerdict>
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
    select: (result: WrongTasksResult) => result.tasks.find((t) => t.id === id),
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

/** Хук-мутация: проверка одного шага лесенки по фото. */
export function useStepSubmit() {
  return useMutation({
    mutationFn: (params: StepSubmitParams) => postStepSubmit(params),
  })
}

// ── Проблемные темы ──
export async function fetchProblemTopics(): Promise<ProblemTopic[]> {
  const res = await apiFetch(`${API_BASE}/trainer/problem-topics`, { headers: authHeaders() })
  const data = (await res.json()) as { topics?: ProblemTopic[] }
  return data.topics ?? []
}

export function useProblemTopics() {
  return useQuery({
    queryKey: ['problem-topics'],
    queryFn: fetchProblemTopics,
    staleTime: 60_000,
  })
}

// ── Verification (closure) ──
export async function startVerification(problemId: number, microSkill?: string | null): Promise<VerificationProblemDTO> {
  const res = await apiFetch(`${API_BASE}/trainer/verification/start`, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ problem_id: problemId, micro_skill: microSkill ?? null }),
  })
  return res.json() as Promise<VerificationProblemDTO>
}

export async function answerVerification(problemId: number, answer: string, microSkill?: string | null): Promise<{ correct: boolean }> {
  const res = await apiFetch(`${API_BASE}/trainer/verification/answer`, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ problem_id: problemId, answer, micro_skill: microSkill ?? null }),
  })
  return res.json() as Promise<{ correct: boolean }>
}

// ── Чат тьютора ──
export async function sendTutorMessage(problemId: number, message: string, decompIdx?: number | null): Promise<TutorChatResponse> {
  const res = await apiFetch(`${API_BASE}/trainer/tutor/chat`, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ problem_id: problemId, message, decomp_idx: decompIdx ?? null }),
  })
  return res.json() as Promise<TutorChatResponse>
}

// ── Climb-down ──
export async function fetchEasier(microSkill: string, excludeIdx?: number | null): Promise<unknown> {
  const params = new URLSearchParams({ micro_skill: microSkill })
  if (excludeIdx != null) params.set('exclude_idx', String(excludeIdx))
  const res = await apiFetch(`${API_BASE}/trainer/easier?${params.toString()}`, { headers: authHeaders() })
  return res.json()
}

// ── Мини-срез (Блок 1.0) ──
export async function startSrez(): Promise<SrezTask[]> {
  const res = await apiFetch(`${API_BASE}/trainer/srez/start`, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  const data = (await res.json()) as { tasks?: SrezTask[] }
  return data.tasks ?? []
}

export async function answerSrez(problemId: number, answer: string, elapsedMs?: number): Promise<{ is_correct: boolean }> {
  const res = await apiFetch(`${API_BASE}/trainer/srez/answer`, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ problem_id: problemId, answer, elapsed_ms: elapsedMs ?? null }),
  })
  return res.json() as Promise<{ is_correct: boolean }>
}

/** Хук-мутация: старт мини-среза (запускает единожды после регистрации). */
export function useSrezStart() {
  return useMutation({
    mutationFn: () => startSrez(),
  })
}

// ── Consent (Блок 1.0) ──
export async function postConsent(photoConsent: boolean): Promise<void> {
  await apiFetch(`${API_BASE}/trainer/consent`, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ photo_consent: photoConsent }),
  })
}
