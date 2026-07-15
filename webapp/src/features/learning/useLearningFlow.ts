import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  advanceLearningLesson,
  answerLearningActivity,
  learningIdentity,
  startLearningLesson,
} from '../../lib/api'
import type { LearningSessionState } from '../../lib/types'

interface PendingSubmission {
  activityId: string
  activityIndex: number
  answer: string
  clientAttemptId: string
  responseTimeMs: number
}

interface ScopedLearningState {
  contextKey: string
  data: LearningSessionState
}

function createAttemptId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `attempt-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

export function useLearningFlow(lessonId: string, identity = learningIdentity()) {
  const contextKey = `${identity}:${lessonId}`
  const query = useQuery({
    queryKey: ['learning-session', identity, lessonId],
    queryFn: ({ signal }) => startLearningLesson(lessonId, signal),
    staleTime: 0,
    gcTime: 0,
    retry: 1,
  })
  const [scopedState, setScopedState] = useState<ScopedLearningState | null>(null)
  const state = scopedState?.contextKey === contextKey ? scopedState.data : null
  const [answer, setAnswer] = useState('')
  const [answerError, setAnswerError] = useState<Error | null>(null)
  const [advanceError, setAdvanceError] = useState<Error | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isAdvancing, setIsAdvancing] = useState(false)
  const pendingRef = useRef<PendingSubmission | null>(null)
  const submittingRef = useRef(false)
  const advancingRef = useRef(false)
  const activityRef = useRef<string | null>(null)
  const startedAtRef = useRef(Date.now())
  const contextRef = useRef(contextKey)
  const submitAbortRef = useRef<AbortController | null>(null)
  const advanceAbortRef = useRef<AbortController | null>(null)

  // Обновляется синхронно с render: завершение старого promise уже не увидит новый контекст.
  contextRef.current = contextKey

  useEffect(() => {
    submitAbortRef.current?.abort()
    advanceAbortRef.current?.abort()
    submitAbortRef.current = null
    advanceAbortRef.current = null
    setAnswer('')
    setAnswerError(null)
    setAdvanceError(null)
    setIsSubmitting(false)
    setIsAdvancing(false)
    pendingRef.current = null
    submittingRef.current = false
    advancingRef.current = false
    activityRef.current = null
  }, [contextKey])

  useEffect(() => {
    // Для уже принятой mutation-state поздний refetch /start не авторитетен.
    if (query.data && scopedState?.contextKey !== contextKey) {
      setScopedState({ contextKey, data: query.data })
    }
  }, [contextKey, query.data, scopedState?.contextKey])

  useEffect(() => {
    const activity = state?.activity
    if (!activity) return
    if (activityRef.current !== activity.id) {
      activityRef.current = activity.id
      startedAtRef.current = Date.now()
      pendingRef.current = null
      setAnswer(activity.last_answer ?? '')
      setAnswerError(null)
      return
    }
    if (activity.last_answer !== null) setAnswer(activity.last_answer)
  }, [state?.activity])

  const changeAnswer = useCallback((value: string) => {
    if (pendingRef.current?.answer !== value) pendingRef.current = null
    setAnswer(value)
    setAnswerError(null)
  }, [])

  const submitAnswer = useCallback(() => {
    const activity = state?.activity
    const normalized = answer.trim()
    if (!activity || activity.role === 'worked' || !normalized || submittingRef.current) return

    const activityIndex = state.progress.completed
    const pending = pendingRef.current
    const submission = pending?.activityId === activity.id
      && pending.activityIndex === activityIndex
      && pending.answer === normalized
      ? pending
      : {
          activityId: activity.id,
          activityIndex,
          answer: normalized,
          clientAttemptId: createAttemptId(),
          responseTimeMs: Math.max(0, Date.now() - startedAtRef.current),
        }
    pendingRef.current = submission
    submittingRef.current = true
    setIsSubmitting(true)
    setAnswerError(null)
    const requestContext = contextKey
    const controller = new AbortController()
    submitAbortRef.current?.abort()
    submitAbortRef.current = controller

    answerLearningActivity({
      lessonId,
      activityId: submission.activityId,
      activityIndex: submission.activityIndex,
      answer: submission.answer,
      clientAttemptId: submission.clientAttemptId,
      responseTimeMs: submission.responseTimeMs,
    }, controller.signal)
      .then((nextState) => {
        if (contextRef.current !== requestContext) return
        pendingRef.current = null
        setScopedState({ contextKey: requestContext, data: nextState })
        const moved = nextState.status === 'completed' || nextState.activity?.id !== submission.activityId
        setAnswer(moved ? '' : (nextState.activity?.last_answer ?? submission.answer))
      })
      .catch((error: unknown) => {
        if (contextRef.current !== requestContext || controller.signal.aborted) return
        setAnswerError(error instanceof Error ? error : new Error('Не удалось проверить ответ'))
      })
      .finally(() => {
        if (contextRef.current !== requestContext || submitAbortRef.current !== controller) return
        submitAbortRef.current = null
        submittingRef.current = false
        setIsSubmitting(false)
      })
  }, [answer, contextKey, lessonId, state])

  const advance = useCallback(() => {
    if (!state?.activity || state.activity.role !== 'worked' || advancingRef.current) return
    advancingRef.current = true
    setIsAdvancing(true)
    setAdvanceError(null)
    const requestContext = contextKey
    const controller = new AbortController()
    advanceAbortRef.current?.abort()
    advanceAbortRef.current = controller
    advanceLearningLesson(lessonId, controller.signal)
      .then((nextState) => {
        if (contextRef.current !== requestContext) return
        setScopedState({ contextKey: requestContext, data: nextState })
      })
      .catch((error: unknown) => {
        if (contextRef.current !== requestContext || controller.signal.aborted) return
        setAdvanceError(error instanceof Error ? error : new Error('Не удалось продолжить'))
      })
      .finally(() => {
        if (contextRef.current !== requestContext || advanceAbortRef.current !== controller) return
        advanceAbortRef.current = null
        advancingRef.current = false
        setIsAdvancing(false)
      })
  }, [contextKey, lessonId, state?.activity])

  const hasCurrentState = state !== null
  return {
    state,
    answer: hasCurrentState ? answer : '',
    changeAnswer,
    submitAnswer,
    advance,
    isLoading: state === null && !query.isError,
    startError: state === null && query.error instanceof Error ? query.error : null,
    retryStart: () => void query.refetch(),
    answerError: hasCurrentState ? answerError : null,
    advanceError: hasCurrentState ? advanceError : null,
    isSubmitting: hasCurrentState ? isSubmitting : false,
    isAdvancing: hasCurrentState ? isAdvancing : false,
  }
}
