import { useCallback, useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { startVerification, answerVerification } from '../../lib/api'
import type { VerificationProblemDTO } from '../../lib/types'

/** Статус закрепления: загрузка / решает / ошибся / закрыл / ошибка сети. */
export type ClosureStatus = 'loading' | 'solving' | 'wrong' | 'correct' | 'error'

interface ClosureState {
  status: ClosureStatus
  problem: VerificationProblemDTO | null
  attempts: number
  check: (value: string) => void
  resume: () => void
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
  const queryClient = useQueryClient()

  useEffect(() => {
    // Холодный кэш wrong-tasks: problem_id ещё 0 (useWrongTask не отдал данные) —
    // ждём реальный id, статус остаётся 'loading', запрос не шлём.
    if (!drillProblemId) return
    let alive = true
    startVerification(drillProblemId, microSkill)
      .then((p) => {
        if (!alive) return
        setProblem(p)
        setStatus('solving')
      })
      .catch(() => {
        if (alive) setStatus('error')
      })
    return () => {
      alive = false
    }
  }, [drillProblemId, microSkill])

  const check = useCallback(
    (value: string) => {
      if (!problem) return
      answerVerification(problem.problem_id, value, microSkill)
        .then((res) => {
          if (res.correct) {
            setStatus('correct')
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
        .catch(() => setStatus('error'))
    },
    [problem, microSkill, onClosed, queryClient],
  )

  const resume = useCallback(() => {
    setStatus((s) => (s === 'wrong' ? 'solving' : s))
  }, [])

  return { status, problem, attempts, check, resume }
}
