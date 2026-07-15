// Типизированный HTTP-клиент для «Работы над ошибками».
// Хуки TanStack Query поверх raw-функций; mock-fallback для DEV.
// Bearer JWT берётся из localStorage по ключу STORAGE_KEY.

import { useSyncExternalStore } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getToken, subscribeToken } from './auth'
import type { WrongTask, Diagnosis, AnalyticsData, ProblemTopic, TutorChatResponse, VerificationProblemDTO, SrezTask, StepVerdict, StepAnswerVerdict, DrillState, LearningPathResponse, LearningSessionState } from './types'
import { MOCK_WRONG_TASKS } from '../features/hub/mock'
import { MOCK_SREZ_TASKS, MOCK_ANALYTICS, MOCK_PROBLEM_TOPICS, MOCK_VERIFICATION } from './devMocks'

/** true — локальная разработка без бэка: подставляем DEV-фикстуры (НЕ в тестах). */
const USE_DEV_MOCK = import.meta.env.DEV && import.meta.env.MODE !== 'test'

/** Базовый URL API — relative same-origin (nginx проксирует /api/ на backend). */
const API_BASE = '/api'

// ——————————————————————————————————
// Кастомные ошибки
// ——————————————————————————————————

/** HTTP-ошибка (не-2xx статус). */
export class ApiError extends Error {
  // erasableSyntaxOnly запрещает parameter properties — объявляем поле явно.
  status: number
  payload: unknown
  constructor(status: number, message: string, payload: unknown = null) {
    super(message)
    this.status = status
    this.payload = payload
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
  const token = getToken()
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

/** Безопасный cache-key ученика: JWT не попадает в query devtools целиком. */
export function learningIdentity(tokenOverride?: string | null): string {
  const token = tokenOverride === undefined ? getToken() : tokenOverride
  if (!token) return 'anonymous'
  try {
    const encoded = token.split('.')[1]
    if (!encoded) return token.slice(-16)
    const payload = JSON.parse(atob(encoded.replace(/-/g, '+').replace(/_/g, '/'))) as { sub?: unknown }
    return typeof payload.sub === 'string' ? payload.sub : token.slice(-16)
  } catch {
    return token.slice(-16)
  }
}

/** Реактивный identity: обновляется и при login/logout, и при смене JWT в другой вкладке. */
export function useLearningIdentity(): string {
  const token = useSyncExternalStore(subscribeToken, getToken, () => null)
  return learningIdentity(token)
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
  if (!res.ok) {
    let payload: unknown = null
    try {
      const source = typeof res.clone === 'function' ? res.clone() : res
      payload = await source.json()
    } catch {
      // Ошибка может быть HTML/plain-text: статус всё равно остаётся источником истины.
    }
    throw new ApiError(res.status, `HTTP ${res.status}: ${url}`, payload)
  }
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
  try {
    const res = await apiFetch(`${API_BASE}/trainer/analytics`, { headers: authHeaders() })
    return await res.json()
  } catch (err) {
    if (USE_DEV_MOCK) return MOCK_ANALYTICS
    throw err
  }
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
  problem_id: number
  photo: File | Blob
}

/**
 * Отправить фото одного шага лесенки для узкой vision-проверки.
 * Тело запроса — multipart/form-data (поля: decomp_idx, step_n, problem_id, photo).
 */
export async function postStepSubmit(params: StepSubmitParams): Promise<StepVerdict> {
  const form = new FormData()
  form.append('decomp_idx', String(params.decomp_idx))
  form.append('step_n', String(params.step_n))
  form.append('problem_id', String(params.problem_id))
  form.append('photo', params.photo)

  const res = await apiFetch(`${API_BASE}/trainer/step-submit`, {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  })
  return res.json() as Promise<StepVerdict>
}

export interface StepAnswerParams {
  problem_id: number
  decomp_idx: number | null
  step_n: number
  answer: string
}

/** Проверить typed-answer на backend, не загружая эталон в браузер. */
export async function postStepAnswer(params: StepAnswerParams): Promise<StepAnswerVerdict> {
  const res = await apiFetch(`${API_BASE}/trainer/step-answer`, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  return res.json() as Promise<StepAnswerVerdict>
}

/** Загрузить подтверждённые шаги для resume после reload. */
export async function fetchDrillState(problemId: number, decompIdx: number | null): Promise<DrillState> {
  const params = new URLSearchParams({ problem_id: String(problemId) })
  if (decompIdx !== null) params.set('decomp_idx', String(decompIdx))
  const res = await apiFetch(`${API_BASE}/trainer/drill-state?${params.toString()}`, {
    headers: authHeaders(),
  })
  return res.json() as Promise<DrillState>
}

// ——————————————————————————————————
// TanStack Query хуки
// ——————————————————————————————————

/** Хук: список задач с ошибками (с кэшем 60 с). */
export function useWrongTasks(days?: number, limit?: number) {
  const identity = useLearningIdentity()
  return useQuery({
    queryKey: ['wrong-tasks', identity, days, limit],
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
  const identity = useLearningIdentity()
  return useQuery({
    queryKey: ['wrong-tasks', identity, undefined, undefined],
    queryFn: () => fetchWrongTasks(),
    staleTime: 60_000,
    select: (result: WrongTasksResult) => result.tasks.find((t) => t.id === id),
  })
}

/** Хук: аналитика тренажёра. */
export function useAnalytics() {
  const identity = useLearningIdentity()
  return useQuery({
    queryKey: ['trainer-analytics', identity],
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

export function useDrillState(problemId: number, decompIdx: number | null) {
  const identity = useLearningIdentity()
  return useQuery({
    queryKey: ['drill-state', identity, problemId, decompIdx],
    queryFn: () => fetchDrillState(problemId, decompIdx),
    staleTime: 0,
  })
}

// ── Проблемные темы ──
export async function fetchProblemTopics(): Promise<ProblemTopic[]> {
  try {
    const res = await apiFetch(`${API_BASE}/trainer/problem-topics`, { headers: authHeaders() })
    const data = (await res.json()) as { topics?: ProblemTopic[] }
    return data.topics ?? []
  } catch (err) {
    if (USE_DEV_MOCK) return MOCK_PROBLEM_TOPICS
    throw err
  }
}

export function useProblemTopics() {
  const identity = useLearningIdentity()
  return useQuery({
    queryKey: ['problem-topics', identity],
    queryFn: fetchProblemTopics,
    staleTime: 60_000,
  })
}

// ── Verification (closure) ──
export async function startVerification(problemId: number, microSkill?: string | null): Promise<VerificationProblemDTO> {
  try {
    const res = await apiFetch(`${API_BASE}/trainer/verification/start`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ problem_id: problemId, micro_skill: microSkill ?? null }),
    })
    return await (res.json() as Promise<VerificationProblemDTO>)
  } catch (err) {
    if (USE_DEV_MOCK) return MOCK_VERIFICATION
    throw err
  }
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
// stepN — ступень лесенки, на которой застрял ученик (бэк фокусирует диалог на ней).
export async function sendTutorMessage(
  problemId: number,
  message: string,
  decompIdx?: number | null,
  stepN?: number | null,
): Promise<TutorChatResponse> {
  const res = await apiFetch(`${API_BASE}/trainer/tutor/chat`, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ problem_id: problemId, message, decomp_idx: decompIdx ?? null, step_n: stepN ?? null }),
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
  try {
    const res = await apiFetch(`${API_BASE}/trainer/srez/start`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
    const data = (await res.json()) as { tasks?: SrezTask[] }
    const tasks = data.tasks ?? []
    if (tasks.length === 0 && USE_DEV_MOCK) return MOCK_SREZ_TASKS
    return tasks
  } catch (err) {
    if (USE_DEV_MOCK) return MOCK_SREZ_TASKS
    throw err
  }
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

// ── Учебный путь ──

export interface AnswerLearningParams {
  lessonId: string
  activityId: string
  activityIndex: number
  answer: string
  clientAttemptId: string
  responseTimeMs?: number
}

export async function fetchLearningPath(signal?: AbortSignal): Promise<LearningPathResponse> {
  const response = await apiFetch(`${API_BASE}/learning/path/current`, {
    headers: authHeaders(),
    signal,
  })
  return response.json() as Promise<LearningPathResponse>
}

async function postLearningState(
  path: 'start' | 'advance',
  lessonId: string,
  signal?: AbortSignal,
): Promise<LearningSessionState> {
  const response = await apiFetch(`${API_BASE}/learning/${path}`, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ lesson_id: lessonId }),
    signal,
  })
  return response.json() as Promise<LearningSessionState>
}

export function startLearningLesson(lessonId: string, signal?: AbortSignal): Promise<LearningSessionState> {
  return postLearningState('start', lessonId, signal)
}

export function advanceLearningLesson(lessonId: string, signal?: AbortSignal): Promise<LearningSessionState> {
  return postLearningState('advance', lessonId, signal)
}

export async function answerLearningActivity(
  params: AnswerLearningParams,
  signal?: AbortSignal,
): Promise<LearningSessionState> {
  try {
    const response = await apiFetch(`${API_BASE}/learning/answer`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lesson_id: params.lessonId,
        activity_id: params.activityId,
        activity_index: params.activityIndex,
        answer: params.answer,
        client_attempt_id: params.clientAttemptId,
        response_time_ms: params.responseTimeMs ?? null,
      }),
      signal,
    })
    return response.json() as Promise<LearningSessionState>
  } catch (error) {
    const detail = error instanceof ApiError && error.status === 409
      ? (error.payload as { detail?: { code?: unknown; state?: unknown } } | null)?.detail
      : null
    const state = detail?.state as Partial<LearningSessionState> | undefined
    if (
      detail?.code === 'stale_activity'
      && typeof state?.session_id === 'number'
      && (state.status === 'active' || state.status === 'completed')
    ) {
      return state as LearningSessionState
    }
    throw error
  }
}

// ── Consent (Блок 1.0) ──
export async function postConsent(photoConsent: boolean): Promise<void> {
  await apiFetch(`${API_BASE}/trainer/consent`, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ photo_consent: photoConsent }),
  })
}
