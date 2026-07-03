import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { startSrez, answerSrez } from '../../lib/api'
import { track } from '../../lib/telemetry'
import type { SrezTask } from '../../lib/types'

/** Пауза после фидбека перед авто-переходом к следующей задаче. */
const FEEDBACK_DELAY_MS = 900

export type SrezPhase = 'answering' | 'feedback'

interface UseSrezResult {
  isLoading: boolean
  isError: boolean
  refetch: () => void
  tasks: SrezTask[]
  currentTask: SrezTask | null
  finished: boolean
  phase: SrezPhase
  feedbackCorrect: boolean | null
  submitting: boolean
  /** Сетевая ошибка именно на шаге проверки ответа (не на старте среза). */
  answerError: boolean
  wrongCount: number
  submit: (value: string) => void
}

/**
 * Состояние мини-среза (Блок 1.0): один запрос startSrez на вход — сервер
 * выбирает 12 задач вразброс тем; дальше клиент листает их локально (index),
 * каждый ответ проверяется отдельным запросом answerSrez. Правильный ответ
 * НИКОГДА не приходит на клиент и не хранится здесь — только вердикт
 * is_correct с сервера (канон §2.5).
 */
export function useSrez(): UseSrezResult {
  const query = useQuery({
    queryKey: ['srez'],
    queryFn: startSrez,
    staleTime: Infinity,
    retry: false,
  })

  const [index, setIndex] = useState(0)
  const [wrongCount, setWrongCount] = useState(0)
  const [feedbackCorrect, setFeedbackCorrect] = useState<boolean | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [answerError, setAnswerError] = useState(false)

  const startTrackedRef = useRef(false)
  const finishTrackedRef = useRef(false)
  const startedAtRef = useRef(Date.now())

  const tasks = query.data ?? []
  const currentTask = tasks[index] ?? null
  const finished = tasks.length > 0 && index >= tasks.length
  const phase: SrezPhase = feedbackCorrect === null ? 'answering' : 'feedback'

  // Телеметрия старта — один раз, после первой успешной загрузки списка задач.
  useEffect(() => {
    if (query.isSuccess && tasks.length > 0 && !startTrackedRef.current) {
      startTrackedRef.current = true
      void track('srez_started')
    }
  }, [query.isSuccess, tasks.length])

  // Таймер текущей задачи — сбрасывается по problem_id, а не по index: иначе
  // отсчёт первой задачи начинался бы ещё до её появления (с рендера хука) и
  // включал бы время загрузки среза в elapsed_ms.
  useEffect(() => {
    startedAtRef.current = Date.now()
  }, [currentTask?.problem_id])

  // Телеметрия финала — один раз, когда все задачи пройдены.
  useEffect(() => {
    if (finished && !finishTrackedRef.current) {
      finishTrackedRef.current = true
      void track('srez_finished', { wrong_count: wrongCount })
    }
  }, [finished, wrongCount])

  const submit = useCallback(
    (value: string) => {
      if (!currentTask || submitting || phase === 'feedback') return
      setSubmitting(true)
      setAnswerError(false)
      const elapsed = Date.now() - startedAtRef.current
      answerSrez(currentTask.problem_id, value, elapsed)
        .then((res) => {
          if (!res.is_correct) setWrongCount((n) => n + 1)
          void track('srez_answered', {
            problem_id: currentTask.problem_id,
            is_correct: res.is_correct,
          })
          setFeedbackCorrect(res.is_correct)
        })
        .catch(() => setAnswerError(true))
        .finally(() => setSubmitting(false))
    },
    [currentTask, submitting, phase],
  )

  // Автопереход к следующей задаче после показа фидбека.
  useEffect(() => {
    if (feedbackCorrect === null) return
    const timer = setTimeout(() => {
      setFeedbackCorrect(null)
      setIndex((i) => i + 1)
    }, FEEDBACK_DELAY_MS)
    return () => clearTimeout(timer)
  }, [feedbackCorrect])

  return {
    isLoading: query.isPending,
    isError: query.isError,
    refetch: () => void query.refetch(),
    tasks,
    currentTask,
    finished,
    phase,
    feedbackCorrect,
    submitting,
    answerError,
    wrongCount,
    submit,
  }
}
