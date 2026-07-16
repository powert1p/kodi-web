import { useCallback, useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { startVerification, answerVerification } from '../../lib/api'
import { track } from '../../lib/telemetry'
import type { VerificationProblemDTO } from '../../lib/types'

/** Статус закрепления: загрузка / решает / ошибся / закрыл / ошибка сети. */
export type ClosureStatus = 'loading' | 'solving' | 'checking' | 'wrong' | 'correct' | 'error'

interface ClosureState {
  status: ClosureStatus
  problem: VerificationProblemDTO | null
  attempts: number
  lastAnswer: string | null
  check: (value: string) => void
  resume: () => void
  retryStart: () => void
}

interface PendingSubmission {
  problemId: number
  answer: string
  clientAttemptId: string
}

function createClientAttemptId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `closure-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

// Живое закрепление: контрольная приходит с verification/start (тот же узел,
// другая задача), проверка — verification/answer (server-side). Верно → 'correct'
// + сервер помечает recurring_errors.resolved. Неверно → 'wrong' (мягкий ретрай).
export function useClosure(
  drillProblemId: number,
  microSkill: string | null,
  onClosed?: () => void,
): ClosureState {
  const [status, setStatus] = useState<ClosureStatus>('loading')
  const [problem, setProblem] = useState<VerificationProblemDTO | null>(null)
  const [attempts, setAttempts] = useState(0)
  const [lastAnswer, setLastAnswer] = useState<string | null>(null)
  const [startAttempt, setStartAttempt] = useState(0)
  const queryClient = useQueryClient()
  // Guard от двойного клика: запрос уже в полёте — повторный check игнорируем.
  const checkInFlight = useRef(false)
  // Сохраняем ключ после ambiguous network failure: retry того же ответа
  // безопасно получает серверный результат, не создавая новый Attempt/BKT update.
  const pendingSubmissionRef = useRef<PendingSubmission | null>(null)
  // Изолирует ответы старой closure-сессии при смене route param или retry.
  const generationRef = useRef(0)

  useEffect(() => {
    const generation = generationRef.current + 1
    generationRef.current = generation
    checkInFlight.current = false
    pendingSubmissionRef.current = null
    setStatus('loading')
    setProblem(null)
    setAttempts(0)
    setLastAnswer(null)
    // Холодный кэш wrong-tasks: problem_id ещё 0 (useWrongTask не отдал данные) —
    // состояние уже очищено, но запрос ждёт реальный id.
    if (!drillProblemId) return
    startVerification(drillProblemId, microSkill)
      .then((p) => {
        if (generationRef.current !== generation) return
        setProblem(p)
        setStatus('solving')
      })
      .catch(() => {
        if (generationRef.current === generation) setStatus('error')
      })
    return () => {
      if (generationRef.current === generation) generationRef.current += 1
    }
  }, [drillProblemId, microSkill, startAttempt])

  const check = useCallback(
    (value: string) => {
      if (!problem) return
      // Двойной клик по проверке — игнорируем повторный вызов, пока первый в полёте.
      if (checkInFlight.current) return
      checkInFlight.current = true
      const generation = generationRef.current
      const answer = value.trim()
      const pending = pendingSubmissionRef.current
      const submission = pending?.problemId === problem.problem_id && pending.answer === answer
        ? pending
        : {
            problemId: problem.problem_id,
            answer,
            clientAttemptId: createClientAttemptId(),
          }
      pendingSubmissionRef.current = submission
      setLastAnswer(answer)
      setStatus('checking')
      answerVerification(problem.problem_id, answer, submission.clientAttemptId, microSkill)
        .then((res) => {
          if (generationRef.current !== generation) return
          pendingSubmissionRef.current = null
          if (res.correct) {
            setStatus('correct')
            void track('closure_passed')
            // Ошибка закрыта на сервере (recurring_errors.resolved) — обновляем
            // кэши hub'а, чтобы список ошибок/проблемных тем сразу отразил закрытие.
            queryClient.invalidateQueries({ queryKey: ['wrong-tasks'] })
            queryClient.invalidateQueries({ queryKey: ['problem-topics'] })
            onClosed?.()
            return
          }
          setAttempts((n) => n + 1)
          setStatus('wrong')
        })
        .catch(() => {
          if (generationRef.current === generation) setStatus('error')
        })
        .finally(() => {
          if (generationRef.current === generation) checkInFlight.current = false
        })
    },
    [problem, microSkill, onClosed, queryClient],
  )

  const resume = useCallback(() => {
    setStatus((s) => (s === 'wrong' || (s === 'error' && problem) ? 'solving' : s))
  }, [problem])

  const retryStart = useCallback(() => {
    if (problem || status !== 'error') return
    setStartAttempt((attempt) => attempt + 1)
  }, [problem, status])

  return { status, problem, attempts, lastAnswer, check, resume, retryStart }
}
